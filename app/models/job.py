import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPk


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class IngestJob(Base, UUIDPk, TimestampMixin):
    """
    A durable, Postgres-backed job queue for document ingestion.

    Uploading a document must return immediately (the old code embedded the
    entire file synchronously inside the HTTP request, blocking the client on
    however long the whole pipeline takes). This table lets a worker process
    claim jobs with `FOR UPDATE SKIP LOCKED`, so multiple workers can run
    concurrently without a broker like Redis/RabbitMQ — appropriate at this
    project's scale, and one less service to operate.
    """

    __tablename__ = "ingest_jobs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.queued, nullable=False, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
