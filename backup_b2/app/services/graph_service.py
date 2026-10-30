import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.models.graph_sync_job import GraphSyncJob
from app.models.security_finding import SecurityFinding
from app.models.browser_event import BrowserEvent
from app.models.visit import Visit
from app.schemas.graph import GraphNode, GraphEdge, GraphVisualizationResponse, GraphStatusResponse
from app.db.base import utc_now


class BaseGraphClient(ABC):
    @abstractmethod
    def check_connection(self) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def upsert_vertex(self, vertex_type: str, vertex_id: str, attributes: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def upsert_edge(
        self,
        source_type: str,
        source_id: str,
        edge_type: str,
        target_type: str,
        target_id: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        pass

    @abstractmethod
    def get_subgraph(self, domain: Optional[str] = None, limit: int = 100) -> Tuple[List[GraphNode], List[GraphEdge]]:
        pass


class MockTigerGraphClient(BaseGraphClient):
    """
    In-memory Mock TigerGraph client for development, offline environments, and automated testing.
    Keeps graph state in memory and mirrors the TigerGraph REST++ behavior.
    """

    def __init__(self):
        self._vertices: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, Dict[str, Any]] = {}
        self._connected = True

    def set_connected(self, state: bool):
        self._connected = state

    def check_connection(self) -> Tuple[bool, str]:
        if self._connected:
            return True, "Mock TigerGraph client operational (Development Mode)"
        return False, "Mock TigerGraph disconnected"

    def upsert_vertex(self, vertex_type: str, vertex_id: str, attributes: Dict[str, Any]) -> bool:
        if not self._connected:
            return False
        key = f"{vertex_type}::{vertex_id}"
        self._vertices[key] = {
            "id": vertex_id,
            "type": vertex_type,
            "label": attributes.get("name") or attributes.get("domain") or vertex_id,
            "attributes": attributes,
        }
        return True

    def upsert_edge(
        self,
        source_type: str,
        source_id: str,
        edge_type: str,
        target_type: str,
        target_id: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if not self._connected:
            return False
        edge_id = f"{source_id}-{edge_type}->{target_id}"
        self._edges[edge_id] = {
            "id": edge_id,
            "source": source_id,
            "target": target_id,
            "label": edge_type,
            "edge_type": edge_type,
            "attributes": attributes or {},
            "is_inferred": (attributes or {}).get("is_inferred", False),
            "confidence": (attributes or {}).get("confidence", "high"),
        }
        return True

    def get_subgraph(self, domain: Optional[str] = None, limit: int = 100) -> Tuple[List[GraphNode], List[GraphEdge]]:
        nodes: List[GraphNode] = []
        for key, v in list(self._vertices.items())[:limit]:
            if domain and domain.lower() not in key.lower():
                continue
            nodes.append(
                GraphNode(
                    id=v["id"],
                    label=v["label"],
                    entity_type=v["type"],
                    properties=v["attributes"],
                )
            )

        edges: List[GraphEdge] = []
        for edge_id, e in list(self._edges.items())[:limit]:
            edges.append(
                GraphEdge(
                    id=e["id"],
                    source=e["source"],
                    target=e["target"],
                    label=e["label"],
                    edge_type=e["edge_type"],
                    properties=e["attributes"],
                    is_inferred=e["is_inferred"],
                    confidence=e["confidence"],
                )
            )

        return nodes, edges


class RealTigerGraphClient(BaseGraphClient):
    """
    Live TigerGraph REST++ Client adapter.
    Uses TigerGraph's built-in REST API endpoints:
    - /echo: heartbeat check
    - /restpp/graph/{graph_name}/vertices/{vertex_type}: upsert vertices
    - /restpp/graph/{graph_name}/edges/{source_type}/{source_id}/{edge_type}/{target_type}/{target_id}: upsert edges
    """

    def __init__(self):
        self.host = settings.TIGERGRAPH_HOST.rstrip("/")
        self.graph_name = settings.TIGERGRAPH_GRAPHNAME
        self.username = settings.TIGERGRAPH_USERNAME
        self.password = settings.TIGERGRAPH_PASSWORD
        self.token = settings.TIGERGRAPH_TOKEN
        self.auth_headers = {}
        if self.token:
            self.auth_headers["Authorization"] = f"Bearer {self.token}"

    def check_connection(self) -> Tuple[bool, str]:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.host}/echo", headers=self.auth_headers)
                if resp.status_code == 200:
                    return True, "TigerGraph live cluster connected"
                return False, f"TigerGraph echo returned HTTP {resp.status_code}"
        except Exception as e:
            return False, f"TigerGraph unreachable: {e}"

    def upsert_vertex(self, vertex_type: str, vertex_id: str, attributes: Dict[str, Any]) -> bool:
        url = f"{self.host}/restpp/graph/{self.graph_name}/vertices/{vertex_type}/{vertex_id}"
        payload = {"attributes": attributes}
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(
                    url,
                    json=payload,
                    headers=self.auth_headers,
                    auth=(self.username, self.password) if not self.token else None,
                )
                return resp.status_code in (200, 201)
        except Exception as e:
            logger.error(f"Error upserting TigerGraph vertex {vertex_type}/{vertex_id}: {e}")
            return False

    def upsert_edge(
        self,
        source_type: str,
        source_id: str,
        edge_type: str,
        target_type: str,
        target_id: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> bool:
        url = (
            f"{self.host}/restpp/graph/{self.graph_name}/edges/"
            f"{source_type}/{source_id}/{edge_type}/{target_type}/{target_id}"
        )
        payload = {"attributes": attributes or {}}
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(
                    url,
                    json=payload,
                    headers=self.auth_headers,
                    auth=(self.username, self.password) if not self.token else None,
                )
                return resp.status_code in (200, 201)
        except Exception as e:
            logger.error(f"Error upserting TigerGraph edge {edge_type}: {e}")
            return False

    def get_subgraph(self, domain: Optional[str] = None, limit: int = 100) -> Tuple[List[GraphNode], List[GraphEdge]]:
        # In degraded or live query, we can query TigerGraph vertices
        url = f"{self.host}/restpp/graph/{self.graph_name}/vertices/Website?limit={limit}"
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.get(
                    url,
                    headers=self.auth_headers,
                    auth=(self.username, self.password) if not self.token else None,
                )
                if resp.status_code == 200:
                    data = resp.json().get("results", [])
                    for item in data:
                        v_id = item.get("v_id")
                        attrs = item.get("attributes", {})
                        nodes.append(
                            GraphNode(
                                id=v_id,
                                label=v_id,
                                entity_type="Website",
                                properties=attrs,
                            )
                        )
        except Exception as e:
            logger.error(f"Failed to query TigerGraph subgraph: {e}")
        return nodes, edges


class GraphService:
    """
    Manages graph synchronizations, background retry queue, and relationship visualization.
    PostgreSQL is the source of record.
    """

    def __init__(self):
        if settings.TIGERGRAPH_ENABLED and not settings.TIGERGRAPH_USE_MOCK:
            self.client: BaseGraphClient = RealTigerGraphClient()
            self.provider_name = "tigergraph"
        else:
            self.client = MockTigerGraphClient()
            self.provider_name = "mock"

    def get_status(self, db: Session) -> GraphStatusResponse:
        connected, msg = self.client.check_connection()
        pending_jobs = db.query(GraphSyncJob).filter(GraphSyncJob.status == "pending").count()
        failed_jobs = db.query(GraphSyncJob).filter(GraphSyncJob.status == "failed").count()
        synced_jobs = db.query(GraphSyncJob).filter(GraphSyncJob.status == "synced").count()

        latest_sync = (
            db.query(GraphSyncJob.synced_at)
            .filter(GraphSyncJob.status == "synced")
            .order_by(GraphSyncJob.synced_at.desc())
            .first()
        )
        last_sync_time = latest_sync[0] if latest_sync else None

        return GraphStatusResponse(
            connected=connected,
            provider=self.provider_name,
            degraded=not connected or (self.provider_name == "mock"),
            status_message=msg,
            pending_sync_jobs=pending_jobs,
            failed_sync_jobs=failed_jobs,
            synced_jobs_count=synced_jobs,
            last_sync_time=last_sync_time,
        )

    def queue_sync_job(
        self, db: Session, entity_type: str, entity_id: str, operation: str = "upsert"
    ) -> GraphSyncJob:
        job = GraphSyncJob(
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            status="pending",
            retry_count=0,
            max_retries=5,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def process_pending_sync_jobs(self, db: Session, batch_size: int = 20) -> int:
        now = utc_now()
        jobs = (
            db.query(GraphSyncJob)
            .filter(
                (GraphSyncJob.status == "pending")
                | ((GraphSyncJob.status == "retrying") & (GraphSyncJob.next_retry_at <= now))
            )
            .order_by(GraphSyncJob.created_at.asc())
            .limit(batch_size)
            .all()
        )

        processed = 0
        for job in jobs:
            job.status = "processing"
            db.commit()

            success = self._execute_sync(db, job)
            if success:
                job.status = "synced"
                job.synced_at = utc_now()
                job.error_details = None
                processed += 1
            else:
                job.retry_count += 1
                if job.retry_count >= job.max_retries:
                    job.status = "failed"
                    job.error_details = {"error": "Exceeded maximum retry limit"}
                else:
                    job.status = "retrying"
                    # Exponential backoff: 2, 4, 8, 16, 32 minutes
                    backoff_minutes = 2 ** job.retry_count
                    job.next_retry_at = utc_now() + timedelta(minutes=backoff_minutes)
                    job.error_details = {"error": "Sync attempt failed, backoff scheduled"}

            db.commit()

        return processed

    def _execute_sync(self, db: Session, job: GraphSyncJob) -> bool:
        connected, _ = self.client.check_connection()
        if not connected:
            return False

        try:
            if job.entity_type == "website":
                # Find event or domain
                event = db.query(BrowserEvent).filter(BrowserEvent.id == job.entity_id).first()
                if not event:
                    return True  # If record deleted, mark complete
                
                # Upsert Website node
                web_ok = self.client.upsert_vertex(
                    vertex_type="Website",
                    vertex_id=event.normalized_domain,
                    attributes={
                        "domain": event.normalized_domain,
                        "scheme": event.scheme,
                        "risk_score": event.preliminary_risk_score,
                    },
                )

                # If referrer exists, add edge
                if event.referrer_domain and event.referrer_domain != event.normalized_domain:
                    self.client.upsert_vertex(
                        vertex_type="Website",
                        vertex_id=event.referrer_domain,
                        attributes={"domain": event.referrer_domain},
                    )
                    self.client.upsert_edge(
                        source_type="Website",
                        source_id=event.referrer_domain,
                        edge_type="REDIRECTED_TO",
                        target_type="Website",
                        target_id=event.normalized_domain,
                        attributes={"is_inferred": False, "confidence": "high"},
                    )
                return web_ok

            elif job.entity_type == "finding":
                finding = db.query(SecurityFinding).filter(SecurityFinding.id == job.entity_id).first()
                if not finding:
                    return True

                # Upsert SecurityFinding node
                find_ok = self.client.upsert_vertex(
                    vertex_type="SecurityFinding",
                    vertex_id=finding.id,
                    attributes={
                        "category": finding.category,
                        "severity": finding.severity,
                        "risk_score": finding.risk_score,
                        "domain": finding.domain,
                    },
                )

                # Upsert GENERATED_FINDING edge
                edge_ok = self.client.upsert_edge(
                    source_type="Website",
                    source_id=finding.domain,
                    edge_type="GENERATED_FINDING",
                    target_type="SecurityFinding",
                    target_id=finding.id,
                    attributes={"is_inferred": False, "confidence": finding.confidence},
                )
                return find_ok and edge_ok

            elif job.entity_type == "visit":
                visit = db.query(Visit).filter(Visit.id == job.entity_id).first()
                if not visit:
                    return True

                self.client.upsert_vertex(
                    vertex_type="Visit",
                    vertex_id=visit.id,
                    attributes={
                        "domain": visit.normalized_domain,
                        "visit_count": visit.visit_count,
                        "last_seen": visit.last_seen_at.isoformat(),
                    },
                )
                self.client.upsert_edge(
                    source_type="Visit",
                    source_id=visit.id,
                    edge_type="VISITED_DOMAIN",
                    target_type="Website",
                    target_id=visit.normalized_domain,
                    attributes={"is_inferred": False, "confidence": "high"},
                )
                return True

            return True
        except Exception as e:
            logger.error(f"Graph sync execution error for job {job.id}: {e}")
            return False

    def get_visualization_subgraph(
        self, db: Session, domain: Optional[str] = None, limit: int = 100
    ) -> GraphVisualizationResponse:
        """
        Produce a frontend-ready node and edge graph.
        Falls back to generating directly from PostgreSQL record-of-truth if TigerGraph is in mock/degraded mode.
        """
        # If mock client has nodes, query it
        nodes, edges = self.client.get_subgraph(domain=domain, limit=limit)

        # If graph is empty (e.g. freshly started), populate from PostgreSQL events & findings
        if not nodes:
            nodes, edges = self._build_graph_from_db(db, domain=domain, limit=limit)

        return GraphVisualizationResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
            is_mock=(self.provider_name == "mock"),
        )

    def _build_graph_from_db(
        self, db: Session, domain: Optional[str] = None, limit: int = 100
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        nodes_dict: Dict[str, GraphNode] = {}
        edges_list: List[GraphEdge] = []

        # Query recent findings
        query = db.query(SecurityFinding).order_by(SecurityFinding.created_at.desc())
        if domain:
            query = query.filter(SecurityFinding.domain == domain.lower())
        findings = query.limit(limit).all()

        for f in findings:
            # Website node
            site_id = f"site::{f.domain}"
            if site_id not in nodes_dict:
                nodes_dict[site_id] = GraphNode(
                    id=site_id,
                    label=f.domain,
                    entity_type="Website",
                    properties={"domain": f.domain, "status": "monitored"},
                )

            # Finding node
            find_id = f"finding::{f.id}"
            nodes_dict[find_id] = GraphNode(
                id=find_id,
                label=f"{f.category.upper()} ({f.severity})",
                entity_type="SecurityFinding",
                properties={
                    "finding_id": f.id,
                    "category": f.category,
                    "severity": f.severity,
                    "risk_score": f.risk_score,
                },
            )

            # GENERATED_FINDING edge
            edges_list.append(
                GraphEdge(
                    id=f"{site_id}-GENERATED_FINDING->{find_id}",
                    source=site_id,
                    target=find_id,
                    label="GENERATED_FINDING",
                    edge_type="GENERATED_FINDING",
                    properties={"risk_score": f.risk_score},
                    is_inferred=False,
                    confidence=f.confidence,
                )
            )

            # Lookalike candidates or external indicators in evidence
            cand = f.evidence.get("candidate_domain") or f.evidence.get("target_domain")
            if cand and cand != f.domain:
                cand_id = f"site::{cand}"
                if cand_id not in nodes_dict:
                    nodes_dict[cand_id] = GraphNode(
                        id=cand_id,
                        label=cand,
                        entity_type="Website",
                        properties={"domain": cand, "role": "target_impersonated"},
                    )
                edges_list.append(
                    GraphEdge(
                        id=f"{site_id}-LOOKALIKE_CANDIDATE->{cand_id}",
                        source=site_id,
                        target=cand_id,
                        label="LOOKALIKE_CANDIDATE",
                        edge_type="CONTACTED",
                        properties={"similarity": f.evidence.get("similarity_score", 0.0)},
                        is_inferred=True,
                        confidence="medium",
                    )
                )

        return list(nodes_dict.values()), edges_list


graph_service = GraphService()
