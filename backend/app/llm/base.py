"""The interface every model provider implements, plus shared errors and retry logic."""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar

from langchain_core.messages import AIMessage, BaseMessage

T = TypeVar("T")


class ProviderError(Exception):
    """Any failure talking to the model provider. `status` becomes the HTTP status code."""

    status = 502


class ConfigError(ProviderError):
    """Provider is not configured, e.g. missing API key."""

    status = 503


class RateLimitError(ProviderError):
    """Provider returned 429 (free-tier quota hit) even after retrying."""

    status = 429


class LLMProvider(ABC):
    name: str
    chat_model: str

    @abstractmethod
    def generate(self, system: str, prompt: str) -> str:
        """Return a plain-text answer in one go (used by the summarise/translate tools)."""

    @abstractmethod
    def generate_json(self, system: str, prompt: str, schema: dict) -> str:
        """Return JSON text that follows `schema` (the provider's structured-output mode).

        The caller still validates it with Pydantic: models can break the schema.
        """

    @abstractmethod
    def chat(
        self,
        system: str,
        messages: list[BaseMessage],
        tools: list[dict],
        on_token: Callable[[str], None] = lambda _: None,
    ) -> AIMessage:
        """One agent step: send the conversation plus tool definitions to the model.

        Text is streamed to `on_token` as it arrives. The returned AIMessage has
        either `tool_calls` (the model wants a tool run) or the final `content`.
        """


def with_retry(
    fn: Callable[[], T],
    is_rate_limit: Callable[[Exception], bool],
    attempts: int = 4,
    base_delay: float = 2.0,
    retry_after: Callable[[Exception], float | None] = lambda e: None,
) -> T:
    """Call fn(); on a rate-limit error wait, then try again.

    The wait is what the provider asked for (`retry_after`), if it said,
    otherwise 2s, 4s, 8s... Any other error is raised straight away.
    After the last attempt we raise RateLimitError.
    """
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as e:
            if not is_rate_limit(e):
                raise
            if attempt == attempts - 1:
                raise RateLimitError("The model provider's rate limit was hit. Wait a minute and try again.") from e
            delay = retry_after(e) or base_delay * 2**attempt
            time.sleep(min(delay + 1, 65))  # +1s margin, never more than ~1 minute
    raise AssertionError("unreachable")
