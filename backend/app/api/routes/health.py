from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings
from app.services.graph_service import graph_service

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Liveness probe: verifies that the FastAPI application is alive."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe: validates database connectivity and external dependency status."""
    db_ok = False
    db_error = None
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_error = str(e)

    graph_status = graph_service.get_status(db)

    is_ready = db_ok
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "ready": is_ready,
        "database": {"connected": db_ok, "error": db_error},
        "graph_database": {
            "connected": graph_status.connected,
            "provider": graph_status.provider,
            "degraded": graph_status.degraded,
            "status_message": graph_status.status_message,
        },
        "threat_intel": {
            "enabled": settings.THREAT_INTEL_ENABLED,
            "provider": settings.THREAT_INTEL_PROVIDER,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

