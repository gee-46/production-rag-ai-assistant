from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.job import IngestJob, JobStatus


def enqueue_ingestion_job(db: Session, *, document_id: uuid.UUID) -> IngestJob:
    job = IngestJob(document_id=document_id, status=JobStatus.queued, run_after=datetime.now(timezone.utc))
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def claim_next_job(db: Session, *, worker_id: str) -> IngestJob | None:
    """
    Atomically claim one queued, due job using `FOR UPDATE SKIP LOCKED`, so
    multiple worker processes can poll the same table concurrently without
    two workers ever processing the same document — the concurrency-safety
    property a broker like Redis/RabbitMQ would normally provide, achieved
    here with plain Postgres so the platform doesn't need an extra service
    just to run background ingestion.
    """
    row = db.execute(
        text(
            """
            SELECT id FROM ingest_jobs
            WHERE status = 'queued' AND run_after <= now()
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )
    ).fetchone()
    if row is None:
        return None

    job = db.get(IngestJob, row.id)
    job.status = JobStatus.running
    job.locked_by = worker_id
    job.attempts += 1
    db.commit()
    db.refresh(job)
    return job


def mark_job_succeeded(db: Session, job: IngestJob) -> None:
    job.status = JobStatus.succeeded
    db.commit()


def mark_job_failed(db: Session, job: IngestJob, error: str) -> None:
    from datetime import timedelta

    job.last_error = error[:2000]
    if job.attempts >= job.max_attempts:
        job.status = JobStatus.failed
    else:
        job.status = JobStatus.queued
        # Exponential backoff before retry.
        job.run_after = datetime.now(timezone.utc) + timedelta(seconds=5 * (2**job.attempts))
    db.commit()
