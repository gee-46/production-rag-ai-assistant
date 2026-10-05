"""
Reranking: the precision stage after hybrid retrieval's high-recall fusion.

Hybrid RRF is deliberately generous (top ~20-40 candidates from two
different signals); a cross-encoder then scores each (query, chunk) pair
jointly — much more accurate than either bi-encoder similarity or lexical
rank alone, at the cost of being too slow to run over the whole corpus.
This mirrors the old project's two-stage idea, but now operating over
hybrid-fused candidates instead of vector-only ones, and via a provider
interface so it can be swapped or faked in tests.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

from app.services.retrieval.vector_search import RetrievedChunk


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        ...


class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        if not chunks:
            return []
        model = self._load()
        pairs = [[query, c.text] for c in chunks]
        scores = model.predict(pairs)
        rescored = [
            RetrievedChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                filename=c.filename,
                text=c.text,
                score=float(s),
                chunk_metadata=c.chunk_metadata,
            )
            for c, s in zip(chunks, scores)
        ]
        rescored.sort(key=lambda c: c.score, reverse=True)
        return rescored[:top_k]


class FakeReranker(Reranker):
    """
    Deterministic reranker for tests: scores each chunk by a stable hash of
    (query, text) so results are reproducible without loading a real
    cross-encoder model.
    """

    def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
        def score(c: RetrievedChunk) -> float:
            h = hashlib.sha256(f"{query}||{c.text}".encode()).hexdigest()
            return int(h[:8], 16) / 0xFFFFFFFF

        rescored = [
            RetrievedChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                filename=c.filename,
                text=c.text,
                score=score(c),
                chunk_metadata=c.chunk_metadata,
            )
            for c in chunks
        ]
        rescored.sort(key=lambda c: c.score, reverse=True)
        return rescored[:top_k]


def build_reranker(provider: str, model_name: str) -> Reranker:
    if provider == "cross_encoder":
        return CrossEncoderReranker(model_name)
    if provider == "fake":
        return FakeReranker()
    raise ValueError(f"Unknown reranker_provider: {provider}")
