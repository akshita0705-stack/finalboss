from typing import List, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_installation_scope, UserScope, get_user_scope
from app.schemas.event import NavigationEventCreate, EventIngestResponse, BrowserEventResponse
from app.models.browser_event import BrowserEvent
from app.services.event_service import event_service
from app.workers.tasks import process_deep_investigation_background

router = APIRouter(prefix="/events", tags=["Browser Events"])


@router.post("", response_model=EventIngestResponse, status_code=status.HTTP_200_OK)
async def ingest_browser_event(
    event_in: NavigationEventCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    installation_id: str = Depends(get_installation_scope),
):
    """
    Ingest a browser navigation event from the Chrome Extension.
    - Validates payload and normalizes URL/domain.
    - Deduplicates repeated submissions safely via idempotency keys.
    - Performs an immediate deterministic risk assessment.
    - Emits live alerts if high-severity risk is identified.
    - Dispatches background deep analysis without delaying the client.
    """
    result = await event_service.ingest_navigation_event(
        db=db,
        event_in=event_in,
        installation_id=installation_id,
    )

    # Schedule background deep analysis if not duplicate
    if not result.is_duplicate:
        background_tasks.add_task(
            process_deep_investigation_background,
            event_id=result.event_id,
        )

    return result


@router.get("", response_model=List[BrowserEventResponse])
def list_browser_events(
    domain: Optional[str] = Query(None, description="Filter by normalized domain"),
    severity: Optional[str] = Query(None, description="Filter by preliminary severity (low, medium, high, critical)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    scope: UserScope = Depends(get_user_scope),
):
    """List the current user's browser events with optional domain, severity, and pagination filters."""
    query = db.query(BrowserEvent).filter(BrowserEvent.installation_id.in_(scope.installation_ids))

    if domain:
        query = query.filter(BrowserEvent.normalized_domain == domain.lower())
    if severity:
        query = query.filter(BrowserEvent.preliminary_severity == severity.lower())

    events = query.order_by(BrowserEvent.created_at.desc()).offset(offset).limit(limit).all()
    return events

