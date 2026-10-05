from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_viewer
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.conversation import ConversationSession, Message, MessageRole
from app.models.user import User
from app.models.workspace import WorkspaceRole, role_at_least
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.embeddings.factory import get_embedding_provider
from app.services.llm.factory import get_llm_provider
from app.services.rag.hallucination import check_groundedness
from app.services.rag.orchestrator import RagOrchestrator
from app.services.retrieval.reranker import build_reranker

router = APIRouter(prefix="/workspaces/{workspace_id}/chat", tags=["chat"])


def _retrieval_config(settings: Settings) -> dict:
    return {
        "vector_top_k": settings.vector_top_k,
        "keyword_top_k": settings.keyword_top_k,
        "rerank_top_k": settings.rerank_top_k,
        "rrf_k": settings.hybrid_rrf_k,
    }


def _get_orchestrator(settings: Settings = Depends(get_settings)) -> RagOrchestrator:
    return RagOrchestrator(
        embedder=get_embedding_provider(),
        reranker=build_reranker(settings.reranker_provider, settings.reranker_model),
        llm=get_llm_provider(),
    )


def _get_or_create_session(
    db: Session, *, workspace_id: uuid.UUID, user_id: uuid.UUID, session_id: uuid.UUID | None
) -> ConversationSession:
    if session_id:
        session = db.get(ConversationSession, session_id)
        if session is None or session.workspace_id != workspace_id:
            raise NotFoundError("Conversation session not found")
        return session
    session = ConversationSession(workspace_id=workspace_id, user_id=user_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("", response_model=ChatResponse)
def chat(
    workspace_id: uuid.UUID,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    membership=Depends(require_viewer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    orchestrator: RagOrchestrator = Depends(_get_orchestrator),
):
    session = _get_or_create_session(
        db, workspace_id=workspace_id, user_id=current_user.id, session_id=payload.session_id
    )
    db.add(Message(session_id=session.id, role=MessageRole.user, content=payload.query))
    db.commit()
    db.refresh(session)

    result = orchestrator.answer(
        db,
        query=payload.query,
        workspace_id=workspace_id,
        user_id=current_user.id,
        is_admin=role_at_least(membership.role, WorkspaceRole.admin),
        session=session,
        retrieval_config=_retrieval_config(settings),
    )

    db.add(
        Message(
            session_id=session.id,
            role=MessageRole.assistant,
            content=result["answer"],
            citations=result["citations"],
            groundedness=result["groundedness"],
        )
    )
    db.commit()

    return ChatResponse(session_id=session.id, **result)


@router.post("/stream")
def chat_stream(
    workspace_id: uuid.UUID,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    membership=Depends(require_viewer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    orchestrator: RagOrchestrator = Depends(_get_orchestrator),
):
    """
    Server-Sent Events stream of answer tokens. The full answer is
    accumulated server-side as it streams so citations and groundedness can
    still be computed and persisted once generation finishes — a client
    disconnecting mid-stream doesn't corrupt conversation history.
    """
    session = _get_or_create_session(
        db, workspace_id=workspace_id, user_id=current_user.id, session_id=payload.session_id
    )
    db.add(Message(session_id=session.id, role=MessageRole.user, content=payload.query))
    db.commit()
    db.refresh(session)

    token_iter, chunks, debug = orchestrator.stream_answer(
        db,
        query=payload.query,
        workspace_id=workspace_id,
        user_id=current_user.id,
        is_admin=role_at_least(membership.role, WorkspaceRole.admin),
        session=session,
        retrieval_config=_retrieval_config(settings),
    )

    def event_source():
        from app.services.rag.citation import build_citations

        yield f"event: session\ndata: {json.dumps({'session_id': str(session.id)})}\n\n"
        full_answer = []
        for token in token_iter:
            full_answer.append(token)
            yield f"data: {json.dumps({'delta': token})}\n\n"

        answer_text = "".join(full_answer)
        citations = build_citations(answer_text, chunks)
        groundedness = check_groundedness(answer_text, chunks)

        # Persist after the stream completes.
        with_db = next(get_db())
        try:
            with_db.add(
                Message(
                    session_id=session.id,
                    role=MessageRole.assistant,
                    content=answer_text,
                    citations=citations,
                    groundedness=groundedness,
                )
            )
            with_db.commit()
        finally:
            with_db.close()

        yield f"event: done\ndata: {json.dumps({'citations': citations, 'groundedness': groundedness, 'retrieval_debug': debug})}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
