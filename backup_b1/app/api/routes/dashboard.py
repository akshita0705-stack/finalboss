from datetime import timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.deps import UserScope, get_user_scope
from app.core.config import settings
from app.db.base import utc_now
from app.db.session import get_db
from app.models.browser_event import BrowserEvent
from app.models.security_finding import SecurityFinding
from app.schemas.dashboard import (
    DashboardHealth, DashboardSummary, HealthItem, RecentEvent, RecentFinding, TrendDay,
)
from app.services.graph_service import graph_service
from app.services.status_labels import STATUS_LABELS, to_status_label

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

LIMITATIONS = (
    "Counts cover only events reported by your linked extension installations. Encrypted traffic is not "
    "inspected, and a missing result is not a safe verdict. LOW_OBSERVED_RISK means no significant issue "
    "was found in the signals checked."
)


def _health(db: Session) -> DashboardHealth:
    try:
        db.execute(text("SELECT 1"))
        backend = HealthItem(ok=True, label="Backend", detail="API and database reachable")
    except Exception:
        backend = HealthItem(ok=False, label="Backend", detail="Database unreachable")

    g = graph_service.get_status(db)
    graph = HealthItem(
        ok=g.connected and not g.degraded,
        label="Graph",
        detail=f"{g.provider}: {g.status_message}"
        + (f" ({g.failed_sync_jobs} failed, {g.pending_sync_jobs} pending sync jobs)" if g.failed_sync_jobs or g.pending_sync_jobs else ""),
    )

    if settings.THREAT_INTEL_ENABLED:
        tp = HealthItem(ok=True, label="Threat provider", detail=f"{settings.THREAT_INTEL_PROVIDER} enabled")
    else:
        tp = HealthItem(ok=False, label="Threat provider", detail="Disabled: reputation checks are not running")
    return DashboardHealth(backend=backend, graph=graph, threat_provider=tp)


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """Overview data for the logged-in user, limited to their own linked installations."""
    ids = scope.installation_ids
    now = utc_now()
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    findings_q = db.query(SecurityFinding).filter(SecurityFinding.installation_id.in_(ids))
    events_q = db.query(BrowserEvent).filter(BrowserEvent.installation_id.in_(ids))

    window = findings_q.filter(SecurityFinding.created_at >= start).all()
    status_counts = {k: 0 for k in STATUS_LABELS}
    trend_map = {}
    for i in range(days):
        d = (start + timedelta(days=i)).date().isoformat()
        trend_map[d] = {k: 0 for k in STATUS_LABELS}
    for f in window:
        label = to_status_label(f.severity)
        status_counts[label] += 1
        day = f.created_at.date().isoformat()
        if day in trend_map:
            trend_map[day][label] += 1

    last_event = events_q.order_by(BrowserEvent.created_at.desc()).first()
    recent_f = findings_q.order_by(SecurityFinding.created_at.desc()).limit(10).all()
    recent_e = events_q.order_by(BrowserEvent.created_at.desc()).limit(10).all()

    return DashboardSummary(
        installations_linked=len(ids),
        last_event_at=last_event.created_at if last_event else None,
        total_events=events_q.count(),
        total_findings=findings_q.count(),
        open_findings=findings_q.filter(SecurityFinding.status.in_(["active", "investigating"])).count(),
        status_counts=status_counts,
        trend=[TrendDay(date=d, counts=c) for d, c in trend_map.items()],
        recent_findings=[
            RecentFinding(
                id=f.id, domain=f.domain, severity=f.severity, status_label=to_status_label(f.severity),
                risk_score=f.risk_score, status=f.status, explanation=f.explanation, created_at=f.created_at,
            ) for f in recent_f
        ],
        recent_events=[
            RecentEvent(
                id=e.id, domain=e.normalized_domain, event_type=e.event_type,
                status_label=to_status_label(e.preliminary_severity), created_at=e.created_at,
            ) for e in recent_e
        ],
        health=_health(db),
        limitations=LIMITATIONS,
    )
