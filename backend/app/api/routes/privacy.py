from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import logger
from app.db.session import get_db
from app.models.browser_event import BrowserEvent
from app.models.daily_report import DailyReport
from app.models.graph_sync_job import GraphSyncJob
from app.models.privacy_models import Alert, BrowserSession, Investigation
from app.models.security_finding import SecurityFinding
from app.models.user import ApiKey, User
from app.models.visit import Visit

router = APIRouter(prefix="/data", tags=["Privacy"])


class DataDeleteResponse(BaseModel):
    deleted: Dict[str, int]
    kept: List[str]
    note: str


def delete_user_browsing_data(db: Session, user: User) -> Dict[str, int]:
    """Delete ONLY this user's browsing data in one transaction. Returns row counts."""
    installation_ids = [
        row[0]
        for row in db.query(ApiKey.installation_id).filter(ApiKey.user_id == user.id).distinct().all()
    ]

    finding_ids = select(SecurityFinding.id).where(
        SecurityFinding.installation_id.in_(installation_ids)
    )
    visit_ids = select(Visit.id).where(
        or_(Visit.installation_id.in_(installation_ids), Visit.user_id == user.id)
    )

    counts: Dict[str, int] = {}
    try:
        # Order matters: remove things that point to other rows first.
        counts["graph_sync_jobs"] = db.execute(
            delete(GraphSyncJob).where(
                or_(GraphSyncJob.entity_id.in_(finding_ids), GraphSyncJob.entity_id.in_(visit_ids))
            )
        ).rowcount
        counts["alerts"] = db.execute(
            delete(Alert).where(or_(Alert.user_id == user.id, Alert.finding_id.in_(finding_ids)))
        ).rowcount
        counts["security_findings"] = db.execute(
            delete(SecurityFinding).where(SecurityFinding.installation_id.in_(installation_ids))
        ).rowcount
        counts["browser_events"] = db.execute(
            delete(BrowserEvent).where(
                or_(BrowserEvent.installation_id.in_(installation_ids), BrowserEvent.user_id == user.id)
            )
        ).rowcount
        counts["visits"] = db.execute(
            delete(Visit).where(
                or_(Visit.installation_id.in_(installation_ids), Visit.user_id == user.id)
            )
        ).rowcount
        counts["daily_reports"] = db.execute(
            delete(DailyReport).where(DailyReport.installation_id.in_(installation_ids))
        ).rowcount
        counts["investigations"] = db.execute(
            delete(Investigation).where(Investigation.user_id == user.id)
        ).rowcount
        counts["browser_sessions"] = db.execute(
            delete(BrowserSession).where(BrowserSession.user_id == user.id)
        ).rowcount
        db.commit()
    except Exception:
        db.rollback()  # all-or-nothing: a failure deletes nothing
        raise

    # Log only counts and the user id, never domains or URLs.
    logger.info(f"User {user.id} deleted browsing data: {counts}")
    return counts


@router.delete("", response_model=DataDeleteResponse)
def delete_my_data(
    confirm: bool = Query(False, description="Must be true. This cannot be undone."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Permanently delete the logged-in user's browsing data. Account and settings are kept."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This permanently deletes your browsing data. Call again with ?confirm=true to proceed.",
        )
    counts = delete_user_browsing_data(db, user)
    return DataDeleteResponse(
        deleted=counts,
        kept=["account", "settings", "extension_api_keys"],
        note=(
            "Database records were deleted. Copies in the graph database (TigerGraph) "
            "are not removed by this endpoint yet."
        ),
    )