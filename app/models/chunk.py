import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.base import Base, TimestampMixin, UUIDPk

settings = get_settings()


class Chunk(Base, UUIDPk, TimestampMixin):
    """
    One retrievable unit of a document.

    Carries everything needed to (a) search it two ways — dense vector
    similarity via pgvector, and lexical relevance via a generated
    Postgres tsvector column — and (b) cite it back to an exact place in
    the source document once it's used in an answer.
    """

    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_workspace_document", "workspace_id", "document_id"),
        # IVFFlat index over the embedding column for approximate nearest-neighbor
        # search at scale; created in the Alembic migration (needs data present /
        # a chosen `lists` parameter), not here.
        Index("ix_chunks_content_tsv", "content_tsv", postgresql_using="gin"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )

    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)  # position within document
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Character offsets into the extracted document text, so a citation can
    # point at an exact span rather than just "chunk #3".
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)

    # Free-form structural metadata: page number, section heading, source
    # filename — extensible without a migration for every new field.
    chunk_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim), nullable=True)

    content_tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', text)", persisted=True), nullable=True
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")  # noqa: F821
