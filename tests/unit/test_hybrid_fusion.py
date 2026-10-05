import uuid

from app.services.retrieval.hybrid import reciprocal_rank_fusion
from app.services.retrieval.vector_search import RetrievedChunk


def _chunk(n, score=0.0):
    return RetrievedChunk(
        chunk_id=uuid.UUID(int=n),
        document_id=uuid.UUID(int=0),
        filename="f.txt",
        text=f"text-{n}",
        score=score,
        chunk_metadata={},
    )


def test_item_ranked_highly_in_both_lists_wins():
    vec = [_chunk(1), _chunk(2), _chunk(3)]
    kw = [_chunk(1), _chunk(4), _chunk(5)]
    fused = reciprocal_rank_fusion([vec, kw], k=60)
    assert fused[0].chunk_id == uuid.UUID(int=1)


def test_fusion_includes_items_present_in_only_one_list():
    vec = [_chunk(1)]
    kw = [_chunk(2)]
    fused = reciprocal_rank_fusion([vec, kw], k=60)
    ids = {c.chunk_id for c in fused}
    assert uuid.UUID(int=1) in ids
    assert uuid.UUID(int=2) in ids


def test_empty_lists_produce_empty_fusion():
    assert reciprocal_rank_fusion([[], []], k=60) == []


def test_fusion_is_sorted_descending_by_score():
    vec = [_chunk(1), _chunk(2), _chunk(3)]
    kw = [_chunk(3), _chunk(1), _chunk(2)]
    fused = reciprocal_rank_fusion([vec, kw], k=60)
    scores = [c.score for c in fused]
    assert scores == sorted(scores, reverse=True)
