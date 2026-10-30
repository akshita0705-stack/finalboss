from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.browser_event import BrowserEvent
from app.models.security_finding import SecurityFinding
from app.models.threat_indicator import ThreatIndicator
from app.models.visit import Visit
from app.services.graph_service import graph_service


class EvidenceRetrievalTools:
    """
    Restricted, authorized backend tools for security evidence retrieval.
    All data is read-only and strictly scoped to authorized database records.
    """

    @staticmethod
    def get_domain_evidence(db: Session, domain: str) -> Dict[str, Any]:
        norm_domain = domain.lower().strip()
        
        # 1. Query findings
        findings = (
            db.query(SecurityFinding)
            .filter(SecurityFinding.domain == norm_domain)
            .order_by(SecurityFinding.created_at.desc())
            .all()
        )

        # 2. Query visits
        visits = (
            db.query(Visit)
            .filter(Visit.normalized_domain == norm_domain)
            .all()
        )
        total_visits = sum(v.visit_count for v in visits)

        # 3. Query threat indicators
        indicators = (
            db.query(ThreatIndicator)
            .filter(ThreatIndicator.normalized_value == norm_domain)
            .all()
        )

        # 4. Query recent events
        recent_events = (
            db.query(BrowserEvent)
            .filter(BrowserEvent.normalized_domain == norm_domain)
            .order_by(BrowserEvent.created_at.desc())
            .limit(5)
            .all()
        )

        findings_data = [
            {
                "finding_id": f.id,
                "category": f.category,
                "severity": f.severity,
                "risk_score": f.risk_score,
                "status": f.status,
                "confidence": f.confidence,
                "explanation": f.explanation,
                "rule_id": f.rule_id,
                "provider_source": f.provider_source,
                "evidence": f.evidence,
                "created_at": f.created_at.isoformat(),
            }
            for f in findings
        ]

        indicators_data = [
            {
                "id": ind.id,
                "provider": ind.provider,
                "verdict": ind.verdict,
                "confidence": ind.confidence,
                "response_status": ind.response_status,
                "observed_at": ind.observed_at.isoformat(),
            }
            for ind in indicators
        ]

        events_data = [
            {
                "event_id": e.id,
                "timestamp": e.created_at.isoformat(),
                "sanitized_url": f"{e.scheme}://{e.normalized_domain}{e.sanitized_url_path}",
                "preliminary_severity": e.preliminary_severity,
                "preliminary_risk_score": e.preliminary_risk_score,
            }
            for e in recent_events
        ]

        return {
            "domain": norm_domain,
            "total_visits": total_visits,
            "findings_count": len(findings),
            "findings": findings_data,
            "threat_indicators": indicators_data,
            "recent_events": events_data,
        }

    @staticmethod
    def get_finding_by_id(db: Session, finding_id: str) -> Optional[Dict[str, Any]]:
        finding = db.query(SecurityFinding).filter(SecurityFinding.id == finding_id).first()
        if not finding:
            return None
        return {
            "finding_id": finding.id,
            "event_id": finding.event_id,
            "domain": finding.domain,
            "category": finding.category,
            "severity": finding.severity,
            "risk_score": finding.risk_score,
            "status": finding.status,
            "confidence": finding.confidence,
            "explanation": finding.explanation,
            "rule_id": finding.rule_id,
            "provider_source": finding.provider_source,
            "evidence": finding.evidence,
            "created_at": finding.created_at.isoformat(),
            "updated_at": finding.updated_at.isoformat(),
        }

    @staticmethod
    def get_graph_context(db: Session, domain: str) -> Dict[str, Any]:
        subgraph = graph_service.get_visualization_subgraph(db=db, domain=domain, limit=20)
        return {
            "node_count": subgraph.total_nodes,
            "edge_count": subgraph.total_edges,
            "nodes": [n.model_dump() for n in subgraph.nodes],
            "edges": [e.model_dump() for e in subgraph.edges],
        }

