from __future__ import annotations

import re

from app.services.retrieval.vector_search import RetrievedChunk

_CITATION_RE = re.compile(r"\[(\d+)\]")


def extract_cited_indices(answer: str) -> set[int]:
    """Return the set of [n] indices the model actually cited (1-based)."""
    return {int(m) for m in _CITATION_RE.findall(answer)}


def build_citations(answer: str, chunks: list[RetrievedChunk]) -> list[dict]:
    """
    Only chunks the model actually cited are returned as citations —
    retrieving 8 chunks and using 2 of them should surface 2 citations, not
    8, or the "citation" becomes meaningless noise.
    """
    cited = extract_cited_indices(answer)
    citations = []
    for i, chunk in enumerate(chunks, start=1):
        if i in cited:
            snippet = chunk.text[:280] + ("..." if len(chunk.text) > 280 else "")
            citations.append(
                {
                    "chunk_id": str(chunk.chunk_id),
                    "document_id": str(chunk.document_id),
                    "filename": chunk.filename,
                    "snippet": snippet,
                    "score": chunk.score,
                }
            )
    return citations
