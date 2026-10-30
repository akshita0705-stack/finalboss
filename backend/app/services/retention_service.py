from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Set

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.base import utc_now
from app.models.browser_event import BrowserEvent
from app.models.graph_sync_job import GraphSyncJob
from app.models.privacy_models import Alert, Investigation, ThreatLookup
from app.models.security_finding import SecurityFinding
from app.models.user import ApiKey, User
from app.models.privacy_models import UserSetting
from app.models.visit import Visit

# A "scope" says which installation ids a purge applies to.
Scope = Callable[[object], object]


def _purge_older_than(
    db: Session,
    cutoff: datetime,
    in_scope: Scope,
    user_id: Optional[str] = None,
) -> Dict[str, int]:
    """Delete rows older than `cutoff` inside one scope. Does NOT commit."""
    old_findings = select(SecurityFinding.id).where(
        in_scope(SecurityFinding.installation_id), SecurityFinding.created_at < cutoff
    )
    old_visits = select(Visit.id).where(
        in_scope(Visit.installation_id), Visit.last_seen_at < cutoff
    )

    counts: Dict[str, int] = {}

    counts["graph_sync_jobs"] = db.execute(
        delete(GraphSyncJob).where(
            or_(GraphSyncJob.entity_id.in_(old_findings), GraphSyncJob.entity_id.in_(old_visits))
        )
    ).rowcount

    alert_condition = Alert.finding_id.in_(old_findings)
    if user_id is not None:
        alert_condition = or_(
            alert_condition, and_(Alert.user_id == user_id, Alert.created_at < cutoff)
        )
    counts["alerts"] = db.execute(delete(Alert).where(alert_condition)).rowcount

    counts["security_findings"] = db.execute(
        delete(SecurityFinding).where(
            in_scope(SecurityFinding.installation_id), SecurityFinding.created_at < cutoff
        )
    ).rowcount
    counts["browser_events"] = db.execute(
        delete(BrowserEvent).where(
            in_scope(BrowserEvent.installation_id), BrowserEvent.created_at < cutoff
        )
    ).rowcount
    counts["visits"] = db.execute(
        delete(Visit).where(in_scope(Visit.installation_id), Visit.last_seen_at < cutoff)
    ).rowcount

    counts["investigations"] = 0
    if user_id is not None:
        counts["investigations"] = db.execute(
            delete(Investigation).where(
                Investigation.user_id == user_id, Investigation.created_at < cutoff
            )
        ).rowcount
    return counts


def _add(total: Dict[str, int], part: Dict[str, int]) -> None:
    for key, value in part.items():
        total[key] = total.get(key, 0) + (value or 0)


def run_retention_cleanup(db: Session, now: Optional[datetime] = None) -> Dict[str, int]:
    """Delete data older than each user's retention period. Returns row counts only."""
    now = now or utc_now()
    totals: Dict[str, int] = {}

    # Which installations belong to which user?
    installations_by_user: Dict[str, Set[str]] = defaultdict(set)
    for user_id, installation_id in (
        db.query(ApiKey.user_id, ApiKey.installation_id).filter(ApiKey.user_id.isnot(None)).all()
    ):
        installations_by_user[user_id].add(installation_id)
    owned_ids = sorted({i for ids in installations_by_user.values() for i in ids})

    retention_by_user = {s.user_id: s.retention_days for s in db.query(UserSetting).all()}

    try:
        for (user_id,) in db.query(User.id).all():
            days = retention_by_user.get(user_id, settings.DATA_RETENTION_DAYS)
            cutoff = now - timedelta(days=days)
            ids = sorted(installations_by_user.get(user_id, set()))
            part = _purge_older_than(
                db, cutoff, in_scope=lambda col, ids=ids: col.in_(ids), user_id=user_id
            )
            _add(totals, part)

        # Installations with no owner left: use the global default period.
        global_cutoff = now - timedelta(days=settings.DATA_RETENTION_DAYS)
        part = _purge_older_than(
            db, global_cutoff, in_scope=lambda col: col.not_in(owned_ids), user_id=None
        )
        _add(totals, part)

        # Expired reputation-cache rows are not needed any more.
        totals["threat_lookups"] = db.execute(
            delete(ThreatLookup).where(ThreatLookup.expires_at < now)
        ).rowcount

        db.commit()
    except Exception:
        db.rollback()  # all-or-nothing
        raise

    logger.info(f"Retention cleanup finished: {totals}")  # counts only, never domains
    return totals