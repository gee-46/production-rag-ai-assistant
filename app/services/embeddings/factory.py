from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.providers import (
    FakeEmbeddingProvider,
    OpenAIEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
)


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "sentence_transformers":
        return SentenceTransformerEmbeddingProvider(settings.embedding_model, settings.embedding_dim)
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("embedding_provider=openai requires OPENAI_API_KEY")
        return OpenAIEmbeddingProvider(settings.openai_api_key, settings.embedding_model, settings.embedding_dim)
    if settings.embedding_provider == "fake":
        return FakeEmbeddingProvider(settings.embedding_dim)
    raise ValueError(f"Unknown embedding_provider: {settings.embedding_provider}")


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return build_embedding_provider(get_settings())
