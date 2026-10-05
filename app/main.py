"""
Application entrypoint.

Unlike the old main.py — which built the vector store, loaded the embedding
model, and embedded every document as module-level code executed at import
time — nothing heavy happens here at import time. Startup work happens in
the `lifespan` context, which FastAPI runs once when the app actually
starts serving, not merely when the module is imported (e.g. by a test or
by Alembic). The app can boot and answer /health even with zero documents,
no GPU, or a cold model cache.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, chat, documents, evaluation, health, workspaces
from app.api.routers import metrics as metrics_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger, request_id_var
from app.core.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger.info(
        "app_starting environment=%s llm_provider=%s embedding_provider=%s",
        settings.environment, settings.llm_provider, settings.embedding_provider,
    )
    yield
    logger.info("app_shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment != "production" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        req_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        token = request_id_var.set(req_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        route_path = route.path if route else request.url.path
        HTTP_REQUESTS_TOTAL.labels(request.method, route_path, response.status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(request.method, route_path).observe(duration)
        response.headers["x-request-id"] = req_id
        return response

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(metrics_router.router)
    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    app.include_router(evaluation.router)

    return app


app = create_app()
