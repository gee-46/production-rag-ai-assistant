"""
Lexical retrieval arm of hybrid search: Postgres full-text search over the
generated tsvector column (see models/chunk.py). Workspace-scoped and
ACL-aware, same as vector_search.py.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.retrieval.vector_search import RetrievedChunk, _visibility_clause


def keyword_search(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    is_admin: bool,
    query: str,
    top_k: int,
) -> list[RetrievedChunk]:
    """
    Lexical retrieval via Postgres full-text search (ts_rank_cd over the
    generated tsvector column). This is the keyword arm of hybrid retrieval:
    it catches exact terms, IDs, acronyms and proper nouns that a dense
    embedding can under-rank, which pure vector search alone misses.
    """
    sql = text(
        f"""
        SELECT c.id, c.document_id, d.filename, c.text, c.chunk_metadata,
               ts_rank_cd(c.content_tsv, plainto_tsquery('english', :q)) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = :workspace_id
          AND d.status = 'ready'
          AND c.content_tsv @@ plainto_tsquery('english', :q)
          AND {_visibility_clause(user_id, is_admin)}
        ORDER BY score DESC
        LIMIT :top_k
        """
    )
    rows = db.execute(sql, {"q": query, "workspace_id": str(workspace_id), "top_k": top_k}).fetchall()
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
