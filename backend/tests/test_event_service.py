import pytest
from datetime import datetime, timezone
from app.services.event_service import event_service
from app.schemas.event import NavigationEventCreate
from app.models.browser_event import BrowserEvent
from app.models.visit import Visit
from app.models.security_finding import SecurityFinding
from app.models.graph_sync_job import GraphSyncJob


@pytest.mark.asyncio
async def test_event_ingestion_and_visit_creation(db_session):
    event_in = NavigationEventCreate(
        url="https://example.com/dashboard",
        event_type="navigation",
        idempotency_key="unique-test-key-001",
    )
    resp = await event_service.ingest_navigation_event(
        db=db_session,
        event_in=event_in,
        installation_id="test-inst-01",
    )
    assert resp.status == "received"
    assert resp.is_duplicate is False
    assert resp.normalized_domain == "example.com"

    # Verify Visit record created
    visit = db_session.query(Visit).filter(Visit.normalized_domain == "example.com").first()
    assert visit is not None
    assert visit.visit_count == 1


@pytest.mark.asyncio
async def test_duplicate_event_does_not_inflate_visits(db_session):
    event_in = NavigationEventCreate(
        url="https://idempotent-test.org/page",
        idempotency_key="fixed-idempotency-key-12345",
    )

    # First ingestion
    resp1 = await event_service.ingest_navigation_event(
        db=db_session,
        event_in=event_in,
        installation_id="test-inst-01",
    )
    assert resp1.is_duplicate is False

    # Check initial visit count
    visit1 = db_session.query(Visit).filter(Visit.normalized_domain == "idempotent-test.org").first()
    assert visit1.visit_count == 1

    # Replay same event (retry submission)
    resp2 = await event_service.ingest_navigation_event(
        db=db_session,
        event_in=event_in,
        installation_id="test-inst-01",
    )
    assert resp2.is_duplicate is True
    assert resp2.status == "deduplicated"

    # Crucial check: visit count MUST NOT inflate!
    visit2 = db_session.query(Visit).filter(Visit.normalized_domain == "idempotent-test.org").first()
    assert visit2.visit_count == 1


@pytest.mark.asyncio
async def test_suspicious_event_generates_finding_and_graph_job(db_session):
    event_in = NavigationEventCreate(
        url="http://paypal-security.evil-site.com/verify-account",
        idempotency_key="suspicious-test-key-999",
    )

    resp = await event_service.ingest_navigation_event(
        db=db_session,
        event_in=event_in,
        installation_id="test-inst-01",
    )

    assert resp.preliminary_assessment.risk_score >= 50
    assert resp.preliminary_assessment.immediate_alert is True

    # Check SecurityFinding created
    finding = db_session.query(SecurityFinding).filter(SecurityFinding.domain == "evil-site.com").first()
    assert finding is not None
    assert finding.severity in ("high", "critical")

    # Check GraphSyncJob queued
    job = db_session.query(GraphSyncJob).filter(GraphSyncJob.entity_id == finding.id).first()
    assert job is not None
    assert job.status == "pending"

