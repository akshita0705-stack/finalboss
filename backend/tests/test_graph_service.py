import pytest
from app.services.graph_service import (
    MockTigerGraphClient,
    GraphService,
)
from app.models.graph_sync_job import GraphSyncJob


def test_mock_tigergraph_client_operations():
    client = MockTigerGraphClient()
    connected, msg = client.check_connection()
    assert connected is True

    # Upsert vertices
    assert client.upsert_vertex("Website", "example.com", {"domain": "example.com"}) is True
    assert client.upsert_vertex("SecurityFinding", "f-100", {"risk_score": 85}) is True

    # Upsert edge with inferred flag
    assert client.upsert_edge(
        source_type="Website",
        source_id="example.com",
        edge_type="GENERATED_FINDING",
        target_type="SecurityFinding",
        target_id="f-100",
        attributes={"is_inferred": False, "confidence": "high"},
    ) is True

    nodes, edges = client.get_subgraph()
    assert len(nodes) == 2
    assert len(edges) == 1
    assert edges[0].label == "GENERATED_FINDING"


def test_graph_sync_job_retry_and_backoff(db_session):
    service = GraphService()
    service.client = MockTigerGraphClient()

    # Create a job with an entity_id that doesn't exist to simulate failure or disconnect
    job = service.queue_sync_job(db_session, entity_type="unknown_type", entity_id="non-existent")
    assert job.status == "pending"

    # Make client fail
    service.client.set_connected(False)

    # Process jobs
    service.process_pending_sync_jobs(db_session, batch_size=5)

    # Refresh job
    db_session.refresh(job)
    assert job.status in ("retrying", "failed")
    assert job.retry_count == 1
    assert job.next_retry_at is not None

