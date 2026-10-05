"""
Hybrid retrieval fusion via Reciprocal Rank Fusion (RRF).

Dense vector similarity and lexical (full-text) relevance scores live on
different, incomparable scales, so fusing them by raw score is unsound.
RRF sidesteps this entirely by fusing on *rank position* instead:
score(doc) = sum over each ranking it appears in of 1 / (k + rank).
It's simple, has no scale-normalization pitfalls, and is the standard
technique real hybrid search systems (Elasticsearch, Weaviate, Azure AI
Search) use for exactly this combination.
"""
from __future__ import annotations

from app.services.retrieval.vector_search import RetrievedChunk


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievedChunk]],
    *,
    k: int = 60,
) -> list[RetrievedChunk]:
    scores: dict[str, float] = {}
    best_chunk: dict[str, RetrievedChunk] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            key = str(chunk.chunk_id)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            # Keep one representative RetrievedChunk per id; fused score is
            # attached afterward, so which list's original score we happen
            # to keep here doesn't matter.
            best_chunk.setdefault(key, chunk)

    fused = [
        RetrievedChunk(
            chunk_id=best_chunk[key].chunk_id,
            document_id=best_chunk[key].document_id,
            filename=best_chunk[key].filename,
            text=best_chunk[key].text,
            score=score,
            chunk_metadata=best_chunk[key].chunk_metadata,
        )
        for key, score in scores.items()
    ]
    fused.sort(key=lambda c: c.score, reverse=True)
    return fused
