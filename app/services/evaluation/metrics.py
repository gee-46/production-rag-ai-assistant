"""
Standard retrieval and generation evaluation metrics.
Supports precision@k, recall@k, mean reciprocal rank (MRR), nDCG@k,
and citation precision / coverage.
"""
from __future__ import annotations
import math


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for r in top_k if r in relevant)
    return hits / len(top_k)


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 1.0 if not retrieved else 0.0
    top_k = retrieved[:k]
    hits = sum(1 for r in top_k if r in relevant)
    return hits / len(relevant)


def mean_reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    if not relevant:
        return 1.0 if not retrieved else 0.0
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant_grades: dict[str, float] | set[str], k: int = 5) -> float:
    """
    Computes Normalized Discounted Cumulative Gain at rank k (nDCG@K).
    """
    if isinstance(relevant_grades, set):
        grades = {doc: 1.0 for doc in relevant_grades}
    else:
        grades = relevant_grades

    if not grades:
        return 1.0 if not retrieved else 0.0

    top_k = retrieved[:k]
    dcg = 0.0
    for i, item in enumerate(top_k, start=1):
        rel = grades.get(item, 0.0)
        dcg += (2.0**rel - 1.0) / math.log2(i + 1)

    # Ideal DCG
    ideal_rels = sorted(grades.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_rels, start=1):
        idcg += (2.0**rel - 1.0) / math.log2(i + 1)

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def citation_precision(citations: list[dict], expected_filenames: set[str]) -> float:
    """Computes fraction of emitted citations that reference an expected relevant document."""
    if not citations:
        return 1.0 if not expected_filenames else 0.0
    valid_citations = sum(1 for c in citations if c.get("filename") in expected_filenames)
    return valid_citations / len(citations)


def citation_coverage(citations: list[dict], expected_filenames: set[str]) -> float:
    """Computes fraction of expected documents that were actually cited in the answer."""
    if not expected_filenames:
        return 1.0 if not citations else 0.0
    cited_filenames = {c.get("filename") for c in citations if c.get("filename")}
    covered = len(cited_filenames.intersection(expected_filenames))
    return covered / len(expected_filenames)
