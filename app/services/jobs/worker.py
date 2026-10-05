"""
Standalone background worker process. Run as a separate container/process
from the API server (see docker/docker-compose.yml, service `worker`):

    python -m app.services.jobs.worker

Polls the Postgres-backed job queue and runs document ingestion jobs. This
is what makes the /documents upload endpoint return immediately instead of
blocking the HTTP request for the duration of chunking + embedding, which
is what the old codebase did.
"""
from __future__ import annotations

import os
import signal
import time
import uuid

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import INGESTION_JOBS_TOTAL
from app.db.session import SessionLocal
from app.services.embeddings.factory import get_embedding_provider
from app.services.ingestion.pipeline import IngestionError, run_ingestion
from app.services.jobs.queue import claim_next_job, mark_job_failed, mark_job_succeeded

logger = get_logger(__name__)

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("worker_shutdown_requested signal=%s", signum)
    _shutdown = True


def run_worker_loop() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    worker_id = f"worker-{os.getpid()}-{uuid.uuid4().hex[:6]}"
    embedder = get_embedding_provider()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("worker_started worker_id=%s", worker_id)

    while not _shutdown:
        db = SessionLocal()
        try:
            job = claim_next_job(db, worker_id=worker_id)
            if job is None:
                db.close()
                time.sleep(settings.job_poll_interval_s)
                continue

            logger.info("job_claimed job_id=%s document_id=%s attempt=%s", job.id, job.document_id, job.attempts)
            try:
                run_ingestion(db, document_id=job.document_id, embedder=embedder, settings=settings)
                mark_job_succeeded(db, job)
                INGESTION_JOBS_TOTAL.labels(outcome="succeeded").inc()
                logger.info("job_succeeded job_id=%s", job.id)
            except IngestionError as exc:
                mark_job_failed(db, job, str(exc))
                INGESTION_JOBS_TOTAL.labels(outcome="failed").inc()
                logger.warning("job_failed job_id=%s error=%s", job.id, exc)
        finally:
            db.close()

    logger.info("worker_stopped worker_id=%s", worker_id)


if __name__ == "__main__":
    run_worker_loop()
