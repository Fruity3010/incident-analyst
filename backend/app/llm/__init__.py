from functools import lru_cache

from app.core import config
from app.llm.base import ConfigError, LLMProvider, ProviderError, RateLimitError

__all__ = ["get_provider", "LLMProvider", "ProviderError", "ConfigError", "RateLimitError"]


@lru_cache
def get_provider() -> LLMProvider:
    if config.LLM_PROVIDER == "gemini":
        from app.llm.gemini import GeminiProvider

        return GeminiProvider()
    if config.LLM_PROVIDER == "ollama":
        from app.llm.ollama import OllamaProvider

        return OllamaProvider()
    raise ConfigError(f"Unknown LLM_PROVIDER '{config.LLM_PROVIDER}'. Use 'gemini' or 'ollama'.")
