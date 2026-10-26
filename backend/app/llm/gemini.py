import base64
import uuid
from collections.abc import Callable

from google import genai
from google.genai import errors, types
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from app import config
from app.llm.base import ConfigError, LLMProvider, ProviderError, with_retry


def _is_rate_limit(e: Exception) -> bool:
    return isinstance(e, errors.APIError) and e.code in (429, 503)


def _retry_delay(e: Exception) -> float | None:
    details = (getattr(e, "details", None) or {}).get("error", {}).get("details", [])
    for d in details:
        if "retryDelay" in d:
            return float(d["retryDelay"].rstrip("s"))
    return None


def _call(fn: Callable):
    try:
        return with_retry(fn, _is_rate_limit, attempts=5, retry_after=_retry_delay)
    except errors.APIError as e:
        if e.code in (400, 401, 403) and "key" in str(e).lower():
            raise ConfigError("Gemini rejected the API key. Check GEMINI_API_KEY in backend/.env.") from e
        raise ProviderError(f"Gemini error: {e.message or e}") from e


def _to_contents(messages: list[BaseMessage]) -> list[types.Content]:
    contents: list[types.Content] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m.content)]))
        elif isinstance(m, AIMessage):
            parts = [types.Part.from_text(text=m.content)] if m.content else []
            signatures = m.additional_kwargs.get("thought_signatures", {})
            for tc in m.tool_calls:
                sig = signatures.get(tc["id"])
                parts.append(
                    types.Part(
                        function_call=types.FunctionCall(name=tc["name"], args=tc["args"]),
                        thought_signature=base64.b64decode(sig) if sig else None,
                    )
                )
            if parts:
                contents.append(types.Content(role="model", parts=parts))
        elif isinstance(m, ToolMessage):
            part = types.Part.from_function_response(name=m.name, response={"result": m.content})
            if contents and contents[-1].role == "user" and contents[-1].parts[0].function_response:
                contents[-1].parts.append(part)
            else:
                contents.append(types.Content(role="user", parts=[part]))
    return contents


def _to_tools(tools: list[dict]) -> list[types.Tool]:
    if not tools:
        return []
    declarations = [
        types.FunctionDeclaration(
            name=t["function"]["name"],
            description=t["function"]["description"],
            parameters_json_schema=t["function"]["parameters"],
        )
        for t in tools
    ]
    return [types.Tool(function_declarations=declarations)]


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self):
        if not config.GEMINI_API_KEY:
            raise ConfigError("GEMINI_API_KEY is not set. Add it to backend/.env (free key: https://aistudio.google.com/apikey).")
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.chat_model = config.GEMINI_CHAT_MODEL

    def generate(self, system: str, prompt: str) -> str:
        cfg = types.GenerateContentConfig(system_instruction=system, temperature=0.2)
        response = _call(lambda: self.client.models.generate_content(model=self.chat_model, contents=prompt, config=cfg))
        return response.text or ""

    def generate_json(self, system: str, prompt: str, schema: dict) -> str:
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=schema,
        )
        response = _call(lambda: self.client.models.generate_content(model=self.chat_model, contents=prompt, config=cfg))
        return response.text or ""

    def chat(self, system, messages, tools, on_token=lambda _: None) -> AIMessage:
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            tools=_to_tools(tools),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        contents = _to_contents(messages)

        def start():
            it = iter(self.client.models.generate_content_stream(model=self.chat_model, contents=contents, config=cfg))
            return next(it, None), it

        first, rest = _call(start)
        text: list[str] = []
        tool_calls: list[dict] = []
        signatures: dict[str, str] = {}

        def handle(chunk):
            candidate = chunk.candidates[0] if chunk.candidates else None
            for part in (candidate.content.parts or []) if candidate and candidate.content else []:
                if part.function_call:
                    call_id = f"call_{uuid.uuid4().hex[:12]}"
                    tool_calls.append({"id": call_id, "name": part.function_call.name, "args": dict(part.function_call.args or {})})
                    if part.thought_signature:
                        signatures[call_id] = base64.b64encode(part.thought_signature).decode()
                elif part.text and not part.thought:
                    text.append(part.text)
                    on_token(part.text)

        if first is not None:
            handle(first)
        try:
            for chunk in rest:
                handle(chunk)
        except errors.APIError as e:
            raise ProviderError(f"Gemini error: {e.message or e}") from e

        return AIMessage(content="".join(text), tool_calls=tool_calls, additional_kwargs={"thought_signatures": signatures})
