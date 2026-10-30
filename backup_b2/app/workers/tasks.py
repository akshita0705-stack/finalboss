import asyncio
from typing import Optional
from sqlalchemy.orm import Session
from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.browser_event import BrowserEvent
from app.models.security_finding import SecurityFinding
from app.services.threat_intel_service import threat_intel_service
from app.services.graph_service import graph_service
from app.services.notification_service import notification_service


async def process_deep_investigation_background(event_id: str):
    """
    Asynchronous background job executing deeper threat-intelligence queries
    and graph synchronizations without delaying browser event ingestion responses.
    """
    db: Session = SessionLocal()
    try:
        event = db.query(BrowserEvent).filter(BrowserEvent.id == event_id).first()
        if not event or event.normalized_domain in ("invalid", "localhost"):
            return

        domain = event.normalized_domain
        logger.info(f"Running deep background investigation for domain: {domain}")

        # 1. Threat Intel Lookup
        intel_result = await threat_intel_service.lookup_and_cache(
            db=db, value=domain, target_type="domain"
        )

        if intel_result.verdict == "malicious":
            # Upgrade existing finding or create new critical finding
            finding = (
                db.query(SecurityFinding)
                .filter(SecurityFinding.event_id == event.id)
                .first()
            )
            if finding:
                finding.severity = "critical"
                finding.risk_score = 95
                finding.category = "threat_intel"
                finding.provider_source = intel_result.provider
                finding.explanation = (
                    f"Confirmed malicious destination according to {intel_result.attribution}."
                )
                evidence = dict(finding.evidence)
                evidence["threat_intel"] = intel_result.raw_details
                finding.evidence = evidence
            else:
                finding = SecurityFinding(
                    event_id=event.id,
                    installation_id=event.installation_id,
                    domain=domain,
                    category="threat_intel",
                    severity="critical",
                    risk_score=95,
                    status="active",
                    confidence="high",
                    explanation=f"Confirmed malicious destination according to {intel_result.attribution}.",
                    rule_id="RULE_THREAT_INTEL_CONFIRMED",
                    provider_source=intel_result.provider,
                    evidence={"threat_intel": intel_result.raw_details},
                )
                db.add(finding)
                db.flush()

            # Update event processing status
            event.processing_status = "enriched"
            event.preliminary_severity = "critical"
            event.preliminary_risk_score = 95
            db.commit()

            # Broadcast live alert for newly confirmed malicious threat
            await notification_service.broadcast_alert(
                event_type="THREAT_INTEL_ALERT",
                payload={
                    "event_id": event.id,
                    "domain": domain,
                    "severity": "critical",
                    "risk_score": 95,
                    "provider": intel_result.provider,
                    "explanation": f"Confirmed threat identified by {intel_result.attribution}.",
                },
                installation_id=event.installation_id,
            )

        # 2. Process Pending Graph Synchronization Jobs
        graph_service.process_pending_sync_jobs(db, batch_size=10)

    except Exception as e:
        logger.error(f"Error during background deep investigation: {e}")
        db.rollback()
    finally:
        db.close()

