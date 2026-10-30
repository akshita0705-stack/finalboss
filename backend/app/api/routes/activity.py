from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import UserScope, get_user_scope
from app.models.browser_event import BrowserEvent
from app.models.visit import Visit
from app.models.security_finding import SecurityFinding
from app.schemas.activity import (
    ActivityAnalyticsResponse,
    VisitResponse,
    DomainVisitStats,
    HourlyDistributionItem,
    ActivityTimelineItem,
)
from app.db.base import utc_now

router = APIRouter(prefix="/activity", tags=["Browsing Activity & Analytics"])


@router.get("", response_model=ActivityAnalyticsResponse)
def get_activity_analytics(
    days: int = Query(7, ge=1, le=90, description="Number of past days to aggregate"),
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """
    Activity timeline and repetition analytics.
    Aggregates navigation volume, unique destinations, repetition count, and timeline.
    """
    cutoff = utc_now() - timedelta(days=days)

    # 1. Events
    ev_query = db.query(BrowserEvent).filter(
        BrowserEvent.created_at >= cutoff,
        BrowserEvent.installation_id.in_(scope.installation_ids),
    )
    events = ev_query.order_by(BrowserEvent.created_at.desc()).all()

    total_events = len(events)
    unique_domains = len(set(e.normalized_domain for e in events))

    # 2. Visits
    vis_query = db.query(Visit).filter(
        Visit.last_seen_at >= cutoff,
        Visit.installation_id.in_(scope.installation_ids),
    )
    visits = vis_query.all()

    repeated_visits_count = sum(v.visit_count - 1 for v in visits if v.visit_count > 1)

    # 3. Top Domains
    domain_map = {}
    for v in visits:
        if v.normalized_domain not in domain_map:
            domain_map[v.normalized_domain] = {"count": 0, "last_seen": v.last_seen_at}
        domain_map[v.normalized_domain]["count"] += v.visit_count
        if v.last_seen_at > domain_map[v.normalized_domain]["last_seen"]:
            domain_map[v.normalized_domain]["last_seen"] = v.last_seen_at

    top_domains = [
        DomainVisitStats(
            domain=dom,
            visit_count=info["count"],
            last_seen_at=info["last_seen"],
            highest_risk_score=0,
            severity="low",
        )
        for dom, info in sorted(domain_map.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    ]

    # 4. Hourly distribution
    hourly_counts = {h: 0 for h in range(24)}
    for e in events:
        hourly_counts[e.created_at.hour] += 1
    hourly_distribution = [
        HourlyDistributionItem(hour=h, count=c) for h, c in sorted(hourly_counts.items())
    ]

    # 5. Timeline items
    timeline = []
    for e in events[:30]:
        has_finding = len(e.findings) > 0 if e.findings else False
        finding_id = e.findings[0].id if has_finding else None
        timeline.append(
            ActivityTimelineItem(
                id=e.id,
                timestamp=e.created_at,
                domain=e.normalized_domain,
                event_type=e.event_type,
                risk_score=e.preliminary_risk_score,
                severity=e.preliminary_severity,
                has_finding=has_finding,
                finding_id=finding_id,
            )
        )

    return ActivityAnalyticsResponse(
        total_events=total_events,
        unique_domains=unique_domains,
        repeated_visits_count=repeated_visits_count,
        top_domains=top_domains,
        hourly_distribution=hourly_distribution,
        recent_timeline=timeline,
    )


@router.get("/visits", response_model=List[VisitResponse])
def list_visits(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """List the current user's distinct tracked navigation visits with repetition counts."""
    query = db.query(Visit).filter(Visit.installation_id.in_(scope.installation_ids))
    if domain:
        query = query.filter(Visit.normalized_domain == domain.lower())
    visits = query.order_by(Visit.last_seen_at.desc()).offset(offset).limit(limit).all()
    return visits

