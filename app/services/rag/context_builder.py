"""
Builds the system + user prompt sent to the LLM.

Unlike the old context_builder (which concatenated raw chunk text with no
identifiers), each chunk here is numbered, and the model is instructed to
cite the numbers it actually used. That numbering is what citation.py later
parses back into real chunk/document references — without it, "citations"
would just be whichever chunks were retrieved, not which ones the model
actually relied on.
"""
from __future__ import annotations

from app.services.retrieval.vector_search import RetrievedChunk

SYSTEM_PROMPT = """You are a precise, grounded assistant answering questions using ONLY the numbered context provided below.

Rules:
- Answer only using information present in the context. If the context does not contain the answer, say so explicitly — do not use outside knowledge.
- After every claim, cite the source number(s) it came from in square brackets, e.g. [1] or [2][3].
- Do not fabricate citation numbers that were not provided.
- Be concise and direct. Do not pad the answer with meta-commentary about what you are doing.
"""


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(f"[{i}] (source: {chunk.filename})\n{chunk.text}")
    return "\n\n".join(parts)


def build_user_prompt(query: str, chunks: list[RetrievedChunk], history: list[tuple[str, str]] | None = None) -> str:
    """
    `history` is a list of (role, content) tuples from prior turns in the
    conversation, oldest first, allowing follow-up questions to resolve
    references like "what about the second one?" against earlier context.
    """
    context_block = build_context_block(chunks) if chunks else "(no relevant context was found)"

    history_block = ""
    if history:
        rendered = "\n".join(f"{role.upper()}: {content}" for role, content in history)
        history_block = f"CONVERSATION SO FAR:\n{rendered}\n\n"

    return f"""{history_block}CONTEXT:
{context_block}

QUESTION:
{query}

ANSWER (cite sources with [n]):"""
