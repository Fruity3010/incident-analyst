"""Ollama provider: runs models locally through Ollama's REST API (no API key needed)."""

import json
import uuid

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from app import config
from app.llm.base import ConfigError, LLMProvider, ProviderError, with_retry


def _is_rate_limit(e: Exception) -> bool:
    return isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429


def _to_messages(system: str, messages: list[BaseMessage]) -> list[dict]:
    """Convert LangChain messages into Ollama's chat format."""
    out = [{"role": "system", "content": system}]
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            calls = [{"function": {"name": tc["name"], "arguments": tc["args"]}} for tc in m.tool_calls]
            out.append({"role": "assistant", "content": m.content, "tool_calls": calls})
        elif isinstance(m, ToolMessage):
            out.append({"role": "tool", "content": m.content, "tool_name": m.name})
    return out


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self):
        self.base_url = config.OLLAMA_BASE_URL.rstrip("/")
        self.chat_model = config.OLLAMA_CHAT_MODEL
        self.http = httpx.Client(base_url=self.base_url, timeout=300)

    def _post(self, body: dict) -> dict:
        def call():
            r = self.http.post("/api/chat", json={"model": self.chat_model, "stream": False, **body})
            r.raise_for_status()
            return r.json()

        try:
            return with_retry(call, _is_rate_limit)
        except httpx.ConnectError as e:
            raise ConfigError(f"Can't reach Ollama at {self.base_url}. Is `ollama serve` running?") from e
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"Ollama error: {e.response.text}") from e

    def _simple(self, system: str, prompt: str) -> list[dict]:
        return [{"role": "system", "content": system}, {"role": "user", "content": prompt}]

    def generate(self, system: str, prompt: str) -> str:
        return self._post({"messages": self._simple(system, prompt), "options": {"temperature": 0.2}})["message"]["content"]

    def generate_json(self, system: str, prompt: str, schema: dict) -> str:
        # Ollama's structured output: `format` takes a JSON schema
        body = {"messages": self._simple(system, prompt), "format": schema, "options": {"temperature": 0}}
        return self._post(body)["message"]["content"]

    def chat(self, system, messages, tools, on_token=lambda _: None) -> AIMessage:
        body = {
            "model": self.chat_model,
            "messages": _to_messages(system, messages),
            "tools": tools,
            "stream": True,
            "options": {"temperature": 0.2},
        }
        text: list[str] = []
        tool_calls: list[dict] = []
        try:
            # Ollama streams one JSON object per line
            with self.http.stream("POST", "/api/chat", json=body) as r:
                if r.status_code >= 400:
                    raise ProviderError(f"Ollama error: {r.read().decode()}")
                for line in r.iter_lines():
                    if not line:
                        continue
                    message = json.loads(line).get("message", {})
                    for tc in message.get("tool_calls") or []:
                        fn = tc["function"]
                        tool_calls.append({"id": f"call_{uuid.uuid4().hex[:12]}", "name": fn["name"], "args": fn.get("arguments") or {}})
                    if message.get("content"):
                        text.append(message["content"])
                        on_token(message["content"])
        except httpx.ConnectError as e:
            raise ConfigError(f"Can't reach Ollama at {self.base_url}. Is `ollama serve` running?") from e
        return AIMessage(content="".join(text), tool_calls=tool_calls)
