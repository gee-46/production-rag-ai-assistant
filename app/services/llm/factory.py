from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.providers import (
    AnthropicProvider,
    FakeLLMProvider,
    GroqProvider,
    OllamaProvider,
    OpenAIProvider,
)


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            raise ValueError("llm_provider=groq requires GROQ_API_KEY")
        return GroqProvider(settings.groq_api_key, settings.llm_model, settings.llm_request_timeout_s, settings.llm_max_retries)
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("llm_provider=openai requires OPENAI_API_KEY")
        return OpenAIProvider(settings.openai_api_key, settings.llm_model, settings.llm_request_timeout_s, settings.llm_max_retries)
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("llm_provider=anthropic requires ANTHROPIC_API_KEY")
        return AnthropicProvider(settings.anthropic_api_key, settings.llm_model, settings.llm_request_timeout_s, settings.llm_max_retries)
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.llm_model, settings.llm_request_timeout_s, settings.llm_max_retries)
    if settings.llm_provider == "fake":
        return FakeLLMProvider()
    raise ValueError(f"Unknown llm_provider: {settings.llm_provider}")


@lru_cache
def get_llm_provider() -> LLMProvider:
    return build_llm_provider(get_settings())
