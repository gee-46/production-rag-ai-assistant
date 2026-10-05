"""
The two retrieval arms that get fused into hybrid search.

Both queries are workspace-scoped and respect document visibility: a
`private` document is only searchable by its uploader or a workspace
admin/owner, enforced with the same predicate the documents API uses for
listing (see api/deps.py `visible_document_filter`). This is the actual
document-level access control the old project's roadmap listed as missing.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    text: str
    score: float
    chunk_metadata: dict


def _visibility_clause(user_id: uuid.UUID, is_admin: bool) -> str:
    if is_admin:
        return "TRUE"
    return f"(d.visibility = 'workspace' OR d.uploaded_by = '{user_id}')"


def vector_search(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    is_admin: bool,
    query_embedding: list[float],
    top_k: int,
) -> list[RetrievedChunk]:
    vec_literal = "[" + ",".join(f"{v:.8f}" for v in query_embedding) + "]"
    sql = text(
        f"""
        SELECT c.id, c.document_id, d.filename, c.text, c.chunk_metadata,
               1 - (c.embedding <=> :qvec) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = :workspace_id
          AND d.status = 'ready'
          AND {_visibility_clause(user_id, is_admin)}
        ORDER BY c.embedding <=> :qvec
        LIMIT :top_k
        """
    )
    rows = db.execute(sql, {"qvec": vec_literal, "workspace_id": str(workspace_id), "top_k": top_k}).fetchall()
    return [
        RetrievedChunk(
            chunk_id=r.id,
            document_id=r.document_id,
            filename=r.filename,
            text=r.text,
            score=float(r.score),
            chunk_metadata=r.chunk_metadata or {},
        )
        for r in rows
    ]
