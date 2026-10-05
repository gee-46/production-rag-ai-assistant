from __future__ import annotations

import hashlib
import struct

from app.core.errors import UpstreamProviderError
from app.core.logging import get_logger
from app.services.embeddings.base import EmbeddingProvider

logger = get_logger(__name__)


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding model via sentence-transformers. Loaded lazily (not at
    import time, unlike the old codebase) so the app can boot and serve
    /health even before the model weights are available, and so tests never
    pay the model-load cost unless they actually exercise this provider.
    """

    def __init__(self, model_name: str, dimension: int):
        self.model_name = model_name
        self.dimension = dimension
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # local import: heavy + optional

            logger.info("loading_embedding_model model=%s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        return model.encode(texts, batch_size=32, show_progress_bar=False).tolist()

    def embed_query(self, text: str) -> list[float]:
        model = self._load()
        return model.encode(text, show_progress_bar=False).tolist()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Remote embeddings via the OpenAI embeddings API."""

    def __init__(self, api_key: str, model_name: str, dimension: int):
        import openai

        self._client = openai.OpenAI(api_key=api_key)
        self.model_name = model_name
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = self._client.embeddings.create(model=self.model_name, input=texts)
        except Exception as exc:  # noqa: BLE001
            raise UpstreamProviderError(f"OpenAI embeddings call failed: {exc}") from exc
        return [d.embedding for d in resp.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class FakeEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic, dependency-free embedding provider for tests and offline
    development. Hashes text into a fixed-length pseudo-random unit vector —
    not semantically meaningful, but stable (same text -> same vector) and
    fast, which is all a test needs to exercise storage/retrieval plumbing
    without downloading model weights or calling a paid API.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _hash_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand the 32-byte digest deterministically to `dimension` floats.
        values: list[float] = []
        seed = digest
        while len(values) < self.dimension:
            seed = hashlib.sha256(seed).digest()
            values.extend(struct.unpack(">8f", seed[:32]) if len(seed) >= 32 else [0.0] * 8)
        values = [v if v == v and abs(v) < 1e6 else 0.0 for v in values[: self.dimension]]  # guard NaN/inf
        norm = sum(v * v for v in values) ** 0.5 or 1.0
        return [v / norm for v in values]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._hash_vector(text)
