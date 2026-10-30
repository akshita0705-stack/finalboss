"""Chrome-extension facing endpoints (/api/v1/extension/*).

The extension sends a minimal, hostname-only payload (no URL path, query, cookies, or page content).
This router adapts it to the internal ingestion pipeline and returns the response shape the extension
expects: ``{"assessment": {"severity": <STATUS_LABEL>, "reason": ..., "finding_id": ..., "redirects": [...]}}``.
A missing or failed assessment is reported as UNKNOWN, never as safe.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import get_installation_scope
from app.core.config import settings
from app.db.session import get_db
from app.schemas.event import NavigationEventCreate
from app.services.event_service import event_service
from app.services.status_labels import to_status_label
from app.workers.tasks import process_deep_investigation_background

router = APIRouter(prefix="/extension", tags=["Chrome Extension"])


class ExtensionEvent(BaseModel):
    event_id: str = Field(..., min_length=8, max_length=64)
    hostname: str = Field(..., min_length=1, max_length=253)
    event_type: str = Field(default="navigation", pattern="^(navigation|error)$")
    timestamp: Optional[datetime] = None
    redirect_from_host: Optional[str] = Field(default=None, max_length=253)
    observed_external_domains: List[str] = Field(default_factory=list, max_length=50)

    @field_validator("hostname", "redirect_from_host")
    @classmethod
    def _no_url_parts(cls, v: Optional[str]) -> Optional[str]:
        # Hostnames only: reject anything that looks like a URL, path, credentials or query.
        if v is None:
            return v
        if any(ch in v for ch in "/?#@ \\"):
            raise ValueError("hostname must not contain URL components")
        return v.strip().lower()


class ExtensionAssessment(BaseModel):
    severity: str
    reason: str
    finding_id: Optional[str] = None
    redirects: List[str] = Field(default_factory=list)
    risk_score: Optional[int] = None
    evidence_quality: str = "preliminary"
    rules_triggered: List[str] = Field(default_factory=list)


class ExtensionEventResponse(BaseModel):
    event_id: str
    is_duplicate: bool
    assessment: ExtensionAssessment


@router.post("/events", response_model=ExtensionEventResponse)
async def submit_extension_event(
    payload: ExtensionEvent,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    installation_id: str = Depends(get_installation_scope),
):
    """Ingest one hostname-level navigation event and return a preliminary assessment.

    Deep checks (threat-intel lookup, graph sync) continue in the background, so the response
    is a *preliminary* assessment (``evidence_quality='preliminary'``).
    """
    event_in = NavigationEventCreate(
        url=f"https://{payload.hostname}/",
        event_type="navigation",
        timestamp=payload.timestamp,
        referrer_url=f"https://{payload.redirect_from_host}/" if payload.redirect_from_host else None,
        idempotency_key=payload.event_id,
        metadata={
            "source": "extension",
            "navigation_outcome": payload.event_type,
            "observed_external_domains": payload.observed_external_domains[:50],
        },
    )
    result = await event_service.ingest_navigation_event(db=db, event_in=event_in, installation_id=installation_id)
    if not result.is_duplicate:
        background_tasks.add_task(process_deep_investigation_background, event_id=result.event_id)

    pre = result.preliminary_assessment
    return ExtensionEventResponse(
        event_id=result.event_id,
        is_duplicate=result.is_duplicate,
        assessment=ExtensionAssessment(
            severity=to_status_label(pre.severity),
            reason=pre.explanation,
            redirects=[payload.redirect_from_host] if payload.redirect_from_host else [],
            risk_score=pre.risk_score,
            evidence_quality=pre.confidence,
            rules_triggered=pre.rules_triggered,
        ),
    )


@router.get("/status")
def extension_status(installation_id: str = Depends(get_installation_scope)):
    """Lightweight connectivity check used by the popup to show a connected/disconnected indicator."""
    return {
        "backend": "connected",
        "threat_provider": settings.THREAT_INTEL_PROVIDER if settings.THREAT_INTEL_ENABLED else "disabled",
        "demo_mode": settings.THREAT_INTEL_PROVIDER == "mock",
    }
