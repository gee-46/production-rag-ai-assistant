from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    settings = get_settings()
    checks = {"database": "unknown"}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if healthy else "degraded",
        "app": settings.app_name,
        "environment": settings.environment,
        "checks": checks,
    }


@router.get("/")
def root():
    return {"message": "Production RAG Platform API — see /docs for the interactive API reference."}
