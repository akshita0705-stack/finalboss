from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    entity_type: str  # Website, Visit, ExternalDomain, ThreatIndicator, SecurityFinding
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str  # VISITED_DOMAIN, REDIRECTED_TO, CONTACTED, MATCHES_INDICATOR, GENERATED_FINDING
    edge_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    is_inferred: bool = False
    confidence: Optional[str] = "high"


class GraphVisualizationResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int
    is_mock: bool = False


class GraphStatusResponse(BaseModel):
    connected: bool
    provider: str  # "tigergraph" or "mock"
    degraded: bool
    status_message: str
    pending_sync_jobs: int
    failed_sync_jobs: int
    synced_jobs_count: int
    last_sync_time: Optional[datetime] = None

