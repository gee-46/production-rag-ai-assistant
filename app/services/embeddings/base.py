"""
Embedding provider abstraction.

The old codebase imported SentenceTransformers directly inside main.py and
loaded the model at module import time, with no way to swap models or test
without downloading a real model. Every provider here implements the same
tiny interface so the rest of the system (chunker, retrieval, ingestion)
never knows which one is active — swap it with one config value.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    dimension: int

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of chunk texts for indexing."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single user query for search."""
