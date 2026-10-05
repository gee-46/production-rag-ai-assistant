import uuid

from app.services.rag.citation import build_citations, extract_cited_indices
from app.services.rag.hallucination import check_groundedness
from app.services.retrieval.vector_search import RetrievedChunk


def _chunk(text, filename="a.txt"):
    return RetrievedChunk(
        chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), filename=filename, text=text, score=1.0, chunk_metadata={}
    )


def test_extract_cited_indices():
    assert extract_cited_indices("Some claim [1] and another [2][3].") == {1, 2, 3}
    assert extract_cited_indices("No citations here.") == set()


def test_build_citations_only_includes_cited_chunks():
    c1 = _chunk("RAG reduces hallucinations.")
    c2 = _chunk("FAISS does similarity search.")
    citations = build_citations("RAG reduces hallucinations [1].", [c1, c2])
    assert len(citations) == 1
    assert citations[0]["filename"] == "a.txt"


def test_groundedness_flags_fabricated_sentence():
    c1 = _chunk("RAG reduces hallucinations by grounding answers in retrieved context.")
    answer = (
        "RAG reduces hallucinations by grounding answers in retrieved context [1]. "
        "The system was invented in 1997 by NASA engineers [1]."
    )
    result = check_groundedness(answer, [c1])
    assert result["supported"] is False
    assert any("NASA" in s for s in result["unsupported_sentences"])


def test_groundedness_passes_fully_supported_answer():
    c1 = _chunk("FAISS is a library for efficient similarity search over dense vectors.")
    answer = "FAISS enables efficient similarity search over dense vectors [1]."
    result = check_groundedness(answer, [c1])
    assert result["supported"] is True
    assert result["unsupported_sentences"] == []


def test_groundedness_with_no_context_and_explicit_refusal_is_supported():
    result = check_groundedness("The context does not contain information about this.", [])
    assert result["supported"] is True


def test_groundedness_with_no_context_and_a_real_claim_is_unsupported():
    result = check_groundedness("The answer is 42.", [])
    assert result["supported"] is False
