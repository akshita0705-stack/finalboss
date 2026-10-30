from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.graph import GraphVisualizationResponse, GraphStatusResponse
from app.services.graph_service import graph_service

router = APIRouter(prefix="/graph", tags=["Graph & Relationships"])


@router.get("/relationships", response_model=GraphVisualizationResponse)
def get_graph_relationships(
    domain: Optional[str] = Query(None, description="Optional domain to center the graph exploration"),
    limit: int = Query(100, ge=10, le=500, description="Max graph entities to return"),
    db: Session = Depends(get_db),
):
    """
    Retrieve nodes and edges for security relationship visualization.
    Vertices: Website, Visit, ExternalDomain, ThreatIndicator, SecurityFinding.
    Edges: VISITED_DOMAIN, REDIRECTED_TO, CONTACTED, MATCHES_INDICATOR, GENERATED_FINDING.
    """
    subgraph = graph_service.get_visualization_subgraph(db=db, domain=domain, limit=limit)
    return subgraph


@router.get("/status", response_model=GraphStatusResponse)
def get_graph_status(db: Session = Depends(get_db)):
    """Retrieve TigerGraph synchronization status, connectivity, and pending sync queue metrics."""
    status_data = graph_service.get_status(db)
    return status_data


@router.post("/sync", status_code=status.HTTP_200_OK)
def trigger_graph_sync_batch(
    batch_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Manually process a batch of pending graph synchronization jobs."""
    processed = graph_service.process_pending_sync_jobs(db, batch_size=batch_size)
    return {"message": "Sync batch processed", "processed_jobs": processed}

