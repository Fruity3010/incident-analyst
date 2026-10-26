import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar

from langchain_core.messages import AIMessage, BaseMessage

T = TypeVar("T")


class ProviderError(Exception):
    status = 502


class ConfigError(ProviderError):
    status = 503


class RateLimitError(ProviderError):
    status = 429


class LLMProvider(ABC):
    name: str
    chat_model: str

    @abstractmethod
    def generate(self, system: str, prompt: str) -> str:
        ...

    @abstractmethod
    def generate_json(self, system: str, prompt: str, schema: dict) -> str:
        ...

    @abstractmethod
    def chat(
        self,
        system: str,
        messages: list[BaseMessage],
        tools: list[dict],
        on_token: Callable[[str], None] = lambda _: None,
    ) -> AIMessage:
        ...


def with_retry(
    fn: Callable[[], T],
    is_rate_limit: Callable[[Exception], bool],
    attempts: int = 4,
    base_delay: float = 2.0,
    retry_after: Callable[[Exception], float | None] = lambda e: None,
) -> T:
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as e:
            if not is_rate_limit(e):
                raise
            if attempt == attempts - 1:
                raise RateLimitError("The model provider's rate limit was hit. Wait a minute and try again.") from e
            delay = retry_after(e) or base_delay * 2**attempt
            time.sleep(min(delay + 1, 65))
    raise AssertionError("unreachable")
