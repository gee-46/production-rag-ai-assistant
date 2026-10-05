from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.document import Document, DocumentStatus
from app.services.chunking.chunker import chunk_text
from app.services.embeddings.base import EmbeddingProvider
from app.services.ingestion.extractors import extract_text

logger = get_logger(__name__)


class IngestionError(Exception):
    pass


def run_ingestion(
    db: Session,
    *,
    document_id: uuid.UUID,
    embedder: EmbeddingProvider,
    settings: Settings,
) -> None:
    """
    Runs the full pipeline for one document: extract text, chunk it,
    embed every chunk, and write chunk rows (including the embedding
    vector). Raises IngestionError on failure; the caller (worker.py) is
    responsible for catching it, recording it on the job row, and marking
    the document as failed.
    """
    document = db.get(Document, document_id)
    if document is None:
        raise IngestionError(f"document {document_id} not found")

    document.status = DocumentStatus.processing
    db.commit()

    try:
        text = extract_text(Path(document.storage_path), document.content_type)
        if not text.strip():
            raise IngestionError("extracted document text is empty")

        spans = chunk_text(
            text, target_tokens=settings.chunk_target_tokens, overlap_tokens=settings.chunk_overlap_tokens
        )
        if not spans:
            raise IngestionError("chunking produced no chunks")

        embeddings = embedder.embed_documents([s.text for s in spans])

        # Replace any existing chunks (re-ingestion / retry case).
        db.query(Chunk).filter(Chunk.document_id == document.id).delete()

        for ordinal, (span, vector) in enumerate(zip(spans, embeddings)):
            db.add(
                Chunk(
                    document_id=document.id,
                    workspace_id=document.workspace_id,
                    ordinal=ordinal,
                    text=span.text,
                    token_count=span.token_count,
                    char_start=span.char_start,
                    char_end=span.char_end,
                    chunk_metadata={"filename": document.filename},
                    embedding=vector,
                )
            )

        document.chunk_count = len(spans)
        document.status = DocumentStatus.ready
        document.error_message = None
        db.commit()
        logger.info("ingestion_succeeded document_id=%s chunks=%s", document.id, len(spans))

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        document = db.get(Document, document_id)
        document.status = DocumentStatus.failed
        document.error_message = str(exc)[:2000]
        db.commit()
        logger.exception("ingestion_failed document_id=%s", document_id)
        raise IngestionError(str(exc)) from exc
