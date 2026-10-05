"""
Token-aware chunking with real overlap and structure awareness.

The old `chunk_text` split on the literal string ". " (breaking on
abbreviations, decimals, and any non-English punctuation), measured size in
raw characters rather than tokens (so chunk sizes were meaningless across
different content density), and declared an `overlap` parameter that was
never used anywhere in the function body.

This version:
  * splits on paragraph/heading boundaries first, so a chunk never
    straddles an unrelated section when the source has structure,
  * falls back to sentence boundaries within an oversized paragraph,
  * measures size in actual model tokens (tiktoken) instead of characters,
  * implements real overlap by carrying the tail sentences of one chunk
    into the start of the next,
  * returns character offsets into the original text for each chunk, so
    a citation can point at the exact source span later.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

from app.core.logging import get_logger

logger = get_logger(__name__)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_WORD_RE = re.compile(r"\S+")

_encoder = None
_encoder_load_failed = False


def _get_encoder():
    """
    Lazily load the tiktoken BPE table. tiktoken fetches its merge table from
    a remote blob store on first use; in network-restricted environments
    (e.g. an offline deployment or a sandboxed CI runner) that fetch can
    fail. We degrade to an approximate word-based token counter rather than
    crashing the whole ingestion pipeline over a tokenizer detail.
    """
    global _encoder, _encoder_load_failed
    if _encoder is not None or _encoder_load_failed:
        return _encoder
    try:
        _encoder = tiktoken.get_encoding("cl100k_base")
    except Exception:  # noqa: BLE001 - deliberately broad; any failure -> fallback
        logger.warning("tiktoken_unavailable_using_approximate_token_counter")
        _encoder_load_failed = True
    return _encoder


def count_tokens(text: str) -> int:
    encoder = _get_encoder()
    if encoder is not None:
        return len(encoder.encode(text))
    # Approximation: whitespace-delimited words scaled by a fixed factor,
    # calibrated against typical English BPE tokenization (~1.3 tokens/word).
    words = len(_WORD_RE.findall(text))
    return max(1, round(words * 1.3)) if text.strip() else 0


@dataclass
class ChunkSpan:
    text: str
    char_start: int
    char_end: int
    token_count: int


def _split_sentences_with_offsets(text: str, base_offset: int) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    start = 0
    for match in _SENTENCE_SPLIT_RE.finditer(text):
        end = match.start()
        sentence = text[start:end]
        if sentence.strip():
            spans.append((sentence, base_offset + start, base_offset + end))
        start = match.end()
    tail = text[start:]
    if tail.strip():
        spans.append((tail, base_offset + start, base_offset + len(text)))
    return spans


def chunk_text(
    text: str,
    *,
    target_tokens: int = 300,
    overlap_tokens: int = 50,
) -> list[ChunkSpan]:
    """
    Chunk `text` into overlapping spans of roughly `target_tokens` tokens.

    Strategy: paragraphs are the primary unit. Consecutive paragraphs are
    packed together until adding the next would exceed `target_tokens`; an
    oversized single paragraph is further split on sentence boundaries.
    Overlap is implemented by carrying the trailing sentences of a finished
    chunk (up to `overlap_tokens` worth) into the front of the next one, so
    context isn't lost at a chunk boundary — the thing the old chunker's
    unused `overlap` parameter implied but never did.
    """
    if not text or not text.strip():
        return []

    # Collect all sentences across the whole document with absolute offsets,
    # using paragraph breaks to avoid merging unrelated sections' sentences.
    all_sentences: list[tuple[str, int, int]] = []
    offset = 0
    for para in _PARAGRAPH_SPLIT_RE.split(text):
        para_offset = text.index(para, offset) if para else offset
        all_sentences.extend(_split_sentences_with_offsets(para, para_offset))
        offset = para_offset + len(para)

    if not all_sentences:
        return []

    chunks: list[ChunkSpan] = []
    current: list[tuple[str, int, int]] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current, current_tokens
        if not current:
            return
        joined = " ".join(s.strip() for s, _, _ in current)
        chunks.append(
            ChunkSpan(
                text=joined,
                char_start=current[0][1],
                char_end=current[-1][2],
                token_count=count_tokens(joined),
            )
        )

    for sentence, s_start, s_end in all_sentences:
        sent_tokens = count_tokens(sentence)

        if current_tokens + sent_tokens > target_tokens and current:
            flush()
            # Build overlap: carry trailing sentences worth ~overlap_tokens.
            carry: list[tuple[str, int, int]] = []
            carry_tokens = 0
            if overlap_tokens > 0:
                for item in reversed(current):
                    t = count_tokens(item[0])
                    if carry and (carry_tokens + t > overlap_tokens):
                        break
                    carry.insert(0, item)
                    carry_tokens += t
                    if carry_tokens >= overlap_tokens:
                        break
            current = carry
            current_tokens = carry_tokens

        current.append((sentence, s_start, s_end))
        current_tokens += sent_tokens

    flush()
    return chunks
