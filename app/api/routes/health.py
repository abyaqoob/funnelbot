"""Health and diagnostic endpoint."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, text

from app.config import settings
from app.database import get_session

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(session: Session = Depends(get_session)):
    """System health check and database connectivity probe."""
    db_status = "connected"
    try:
        session.exec(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "FunnelBot",
        "version": "0.1.0",
        "database": db_status,
        "demo_mode": settings.DEMO_MODE,
        "llm_provider": settings.LLM_PROVIDER,
        "timestamp": datetime.now(UTC).isoformat(),
    }
