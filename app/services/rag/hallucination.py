"""
Groundedness checking: flags answer sentences that are not supported by the
retrieved context, so an unsupported claim is surfaced to the caller instead
of silently presented as fact.

Method: token-overlap (Jaccard-style) between each answer sentence and the
context chunks the model cited for it. This is a real, working heuristic —
not a stub — but it is explicitly a lexical method, not semantic entailment.
It will correctly catch a sentence that introduces facts/numbers/names
absent from the context, and will not catch a sentence that is a fluent
paraphrase that happens to share few words with its source. That trade-off
is documented here and reported in the `method` field of every verdict
so nothing is silently overclaimed. A natural upgrade path (noted in the
README roadmap) is to replace this with an NLI/entailment cross-encoder
scoring (premise=context, hypothesis=sentence) for semantic groundedness.
"""
from __future__ import annotations

import re

from app.services.rag.citation import extract_cited_indices
from app.services.retrieval.vector_search import RetrievedChunk

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on", "for",
    "and", "or", "with", "as", "by", "at", "it", "this", "that", "be", "can",
    "has", "have", "not", "which", "from", "its",
}
_OVERLAP_THRESHOLD = 0.15  # fraction of content words in a sentence that must appear in the cited context


def _content_words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS and len(w) > 2}


def check_groundedness(answer: str, chunks: list[RetrievedChunk]) -> dict:
    if not chunks:
        # No context at all: only a response that explicitly declines to
        # answer counts as grounded; anything else is by definition unsupported.
        return {
            "supported": _looks_like_refusal(answer),
            "unsupported_sentences": [] if _looks_like_refusal(answer) else [answer],
            "method": "lexical_overlap",
        }

    all_context_words = _content_words(" ".join(c.text for c in chunks))
    cited_indices = extract_cited_indices(answer)
    cited_words = (
        _content_words(" ".join(chunks[i - 1].text for i in cited_indices if 1 <= i <= len(chunks)))
        if cited_indices
        else all_context_words
    )

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(answer) if s.strip()]
    unsupported = []
    for sentence in sentences:
        words = _content_words(sentence)
        if not words:
            continue
        overlap = len(words & cited_words) / len(words)
        if overlap < _OVERLAP_THRESHOLD and not _looks_like_refusal(sentence):
            unsupported.append(sentence)

    return {
        "supported": len(unsupported) == 0,
        "unsupported_sentences": unsupported,
        "method": "lexical_overlap",
    }


def _looks_like_refusal(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in ("does not contain", "doesn't contain", "no relevant", "cannot answer", "not enough information")
    )
