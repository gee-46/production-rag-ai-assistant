from __future__ import annotations

import time
import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.metrics import (
    RAG_GENERATION_DURATION_SECONDS,
    RAG_RETRIEVAL_DURATION_SECONDS,
    RAG_UNGROUNDED_ANSWERS_TOTAL,
)
from app.models.conversation import ConversationSession
from app.services.embeddings.base import EmbeddingProvider
from app.services.llm.base import LLMProvider
from app.services.rag.citation import build_citations
from app.services.rag.context_builder import SYSTEM_PROMPT, build_user_prompt
from app.services.rag.hallucination import check_groundedness
from app.services.retrieval.hybrid import reciprocal_rank_fusion
from app.services.retrieval.keyword_search import keyword_search
from app.services.retrieval.reranker import Reranker
from app.services.retrieval.vector_search import RetrievedChunk, vector_search

logger = get_logger(__name__)

HISTORY_TURNS = 6  # last N messages included as conversation context


class RagOrchestrator:
    def __init__(self, embedder: EmbeddingProvider, reranker: Reranker, llm: LLMProvider):
        self.embedder = embedder
        self.reranker = reranker
        self.llm = llm

    def retrieve(
        self,
        db: Session,
        *,
        query: str,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool,
        vector_top_k: int,
        keyword_top_k: int,
        rerank_top_k: int,
        rrf_k: int,
    ) -> tuple[list[RetrievedChunk], dict]:
        query_embedding = self.embedder.embed_query(query)

        start = time.perf_counter()
        vec_results = vector_search(
            db, workspace_id=workspace_id, user_id=user_id, is_admin=is_admin,
            query_embedding=query_embedding, top_k=vector_top_k,
        )
        kw_results = keyword_search(
            db, workspace_id=workspace_id, user_id=user_id, is_admin=is_admin,
            query=query, top_k=keyword_top_k,
        )
        fused = reciprocal_rank_fusion([vec_results, kw_results], k=rrf_k)
        reranked = self.reranker.rerank(query, fused, top_k=rerank_top_k)
        RAG_RETRIEVAL_DURATION_SECONDS.observe(time.perf_counter() - start)

        debug = {
            "vector_candidates": len(vec_results),
            "keyword_candidates": len(kw_results),
            "fused_candidates": len(fused),
            "final_chunks": len(reranked),
        }
        return reranked, debug

    def answer(
        self,
        db: Session,
        *,
        query: str,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool,
        session: ConversationSession,
        retrieval_config: dict,
    ) -> dict:
        history = [
            (m.role.value, m.content)
            for m in session.messages[-HISTORY_TURNS:]
        ]

        chunks, debug = self.retrieve(
            db, query=query, workspace_id=workspace_id, user_id=user_id, is_admin=is_admin, **retrieval_config
        )

        user_prompt = build_user_prompt(query, chunks, history=history)
        gen_start = time.perf_counter()
        answer_text = self.llm.generate(SYSTEM_PROMPT, user_prompt)
        RAG_GENERATION_DURATION_SECONDS.observe(time.perf_counter() - gen_start)

        citations = build_citations(answer_text, chunks)
        groundedness = check_groundedness(answer_text, chunks)

        if not groundedness["supported"]:
            RAG_UNGROUNDED_ANSWERS_TOTAL.inc()
            logger.warning(
                "ungrounded_answer session=%s unsupported_count=%s",
                session.id, len(groundedness["unsupported_sentences"]),
            )

        return {
            "answer": answer_text,
            "citations": citations,
            "groundedness": groundedness,
            "retrieval_debug": debug,
        }

    def stream_answer(
        self,
        db: Session,
        *,
        query: str,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool,
        session: ConversationSession,
        retrieval_config: dict,
    ):
        """
        Yields text tokens as they're generated. Citations/groundedness can
        only be computed once the full answer is known, so the caller
        (chat router) accumulates the streamed text and computes those after
        the stream ends, then persists the final Message with both.
        """
        history = [(m.role.value, m.content) for m in session.messages[-HISTORY_TURNS:]]
        chunks, debug = self.retrieve(
            db, query=query, workspace_id=workspace_id, user_id=user_id, is_admin=is_admin, **retrieval_config
        )
        user_prompt = build_user_prompt(query, chunks, history=history)
        return self.llm.stream(SYSTEM_PROMPT, user_prompt), chunks, debug
