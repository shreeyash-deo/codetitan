from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from app.services.ai.gemini_client import gemini_client

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check endpoint")
def health_check(db: Session = Depends(get_db)):
    """
    Service health probe checking API status, environment metadata, and database connectivity.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ai", summary="AI provider diagnostic probe")
def ai_health_check(probe: bool = Query(False, description="Perform live minimal authenticated API probe")):
    """
    Backend diagnostic check for the configured AI provider.
    - probe=false (default): reports provider, model, key presence (redacted), and readiness without consuming API quota.
    - probe=true: executes a minimal test ping to confirm end-to-end authentication and JSON response parsing.
    Credentials and secrets are strictly redacted.
    """
    return gemini_client.check_health(probe_live=probe)
