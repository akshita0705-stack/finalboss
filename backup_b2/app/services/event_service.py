import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.models.browser_event import BrowserEvent
from app.models.visit import Visit
from app.models.security_finding import SecurityFinding
from app.schemas.event import NavigationEventCreate, EventIngestResponse, PreliminaryAssessment
from app.services.url_normalizer import UrlNormalizer, NormalizedUrl
from app.services.detection_service import detection_engine, AssessmentResult
from app.services.graph_service import graph_service
from app.services.notification_service import notification_service
from app.db.base import utc_now


class EventService:
    @staticmethod
    def generate_idempotency_key(
        installation_id: str,
        sanitized_url: str,
        client_timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Generate a stable idempotency key for navigation events.
        If the client retries the exact same navigation within a 10-second window,
        the hash matches, preventing duplicate event creation and visit inflation.
        """
        ts = client_timestamp or utc_now()
        # Round timestamp to 10-second bucket
        bucket = int(ts.timestamp() // 10)
        raw_key = f"{installation_id}::{sanitized_url}::{bucket}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def ingest_navigation_event(
        self,
        db: Session,
        event_in: NavigationEventCreate,
        installation_id: str,
        user_id: Optional[str] = None,
    ) -> EventIngestResponse:
        # 1. URL and Domain Normalization
        norm_url = UrlNormalizer.normalize(event_in.url, strip_query_strings=True)
        client_ts = event_in.timestamp or utc_now()

        # 2. Derive Idempotency Key
        idempotency_key = event_in.idempotency_key or self.generate_idempotency_key(
            installation_id=installation_id,
            sanitized_url=norm_url.sanitized_url if norm_url.is_valid else event_in.url,
            client_timestamp=client_ts,
        )

        # 3. Check for Duplicate Submission
        existing_event = (
            db.query(BrowserEvent)
            .filter(BrowserEvent.idempotency_key == idempotency_key)
            .first()
        )

        if existing_event:
            logger.info(
                f"Duplicate event detected for idempotency_key={idempotency_key[:12]}... (Visit count NOT inflated)"
            )
            return EventIngestResponse(
                event_id=existing_event.id,
                idempotency_key=existing_event.idempotency_key,
                status="deduplicated",
                is_duplicate=True,
                normalized_domain=existing_event.normalized_domain,
                sanitized_url_path=existing_event.sanitized_url_path,
                preliminary_assessment=PreliminaryAssessment(
                    risk_score=existing_event.preliminary_risk_score,
                    severity=existing_event.preliminary_severity,
                    confidence="high",
                    immediate_alert=existing_event.preliminary_severity in ("high", "critical"),
                    explanation="Duplicate event submission replayed; existing assessment returned.",
                    rules_triggered=[],
                ),
                timestamp=existing_event.created_at,
            )

        # 4. Instant Deterministic Security Assessment
        assessment: AssessmentResult = detection_engine.assess_url(norm_url)

        # 5. Persist Browser Event
        new_event = BrowserEvent(
            idempotency_key=idempotency_key,
            installation_id=installation_id,
            user_id=user_id,
            normalized_domain=norm_url.domain if norm_url.is_valid else "invalid",
            sanitized_url_path=norm_url.privacy_minimized_path if norm_url.is_valid else "/",
            scheme=norm_url.scheme if norm_url.is_valid else "http",
            event_type=event_in.event_type or "navigation",
            source="chrome_extension",
            processing_status="assessed",
            preliminary_risk_score=assessment.risk_score,
            preliminary_severity=assessment.severity,
            referrer_domain=norm_url.domain if event_in.referrer_url else None,
            redirect_chain=[],
            metadata_json=event_in.metadata or {},
            client_timestamp=client_ts,
        )
        db.add(new_event)
        db.flush()  # Generates new_event.id

        # 6. Update Visit Counter (Idempotent: only increments on true new visits)
        if norm_url.is_valid:
            self._update_visit_record(
                db=db,
                installation_id=installation_id,
                user_id=user_id,
                domain=norm_url.domain,
                privacy_minimized_path=norm_url.privacy_minimized_path,
                timestamp=client_ts,
            )

        # 7. Create Security Finding if risk identified
        if assessment.risk_score > 0 and assessment.rules_triggered:
            primary_rule = assessment.rules_triggered[0]
            category = "suspicious_domain"
            if "LOOKALIKE" in primary_rule:
                category = "homograph"
            elif "DECEPTIVE" in primary_rule:
                category = "phishing"
            elif "IP_HOST" in primary_rule:
                category = "deceptive_structure"
            elif "KNOWN_INDICATOR" in primary_rule:
                category = "threat_intel"

            finding = SecurityFinding(
                event_id=new_event.id,
                installation_id=installation_id,
                domain=norm_url.domain if norm_url.is_valid else "invalid",
                category=category,
                severity=assessment.severity,
                risk_score=assessment.risk_score,
                status="active",
                confidence=assessment.confidence,
                explanation=assessment.explanation,
                rule_id=primary_rule,
                provider_source="deterministic_detection_engine",
                evidence={
                    "rules": assessment.rules_triggered,
                    "signals": assessment.contributing_signals,
                    "lookalike_candidate": assessment.lookalike_candidate,
                    "host": norm_url.host,
                    "sanitized_url": norm_url.sanitized_url,
                },
            )
            db.add(finding)
            db.flush()

            # Queue graph synchronization job
            graph_service.queue_sync_job(
                db=db, entity_type="finding", entity_id=finding.id, operation="upsert"
            )

        # Queue website graph sync job
        graph_service.queue_sync_job(
            db=db, entity_type="website", entity_id=new_event.id, operation="upsert"
        )

        db.commit()

        # 8. Dispatch Real-Time Alert if high or critical
        if assessment.immediate_alert:
            await notification_service.broadcast_alert(
                event_type="SECURITY_ALERT",
                payload={
                    "event_id": new_event.id,
                    "domain": norm_url.domain,
                    "severity": assessment.severity,
                    "risk_score": assessment.risk_score,
                    "explanation": assessment.explanation,
                    "rules_triggered": assessment.rules_triggered,
                    "sanitized_url": norm_url.sanitized_url,
                },
                installation_id=installation_id,
            )

        return EventIngestResponse(
            event_id=new_event.id,
            idempotency_key=new_event.idempotency_key,
            status="received",
            is_duplicate=False,
            normalized_domain=new_event.normalized_domain,
            sanitized_url_path=new_event.sanitized_url_path,
            preliminary_assessment=PreliminaryAssessment(
                risk_score=assessment.risk_score,
                severity=assessment.severity,
                confidence=assessment.confidence,
                immediate_alert=assessment.immediate_alert,
                explanation=assessment.explanation,
                rules_triggered=assessment.rules_triggered,
            ),
            timestamp=new_event.created_at,
        )

    def _update_visit_record(
        self,
        db: Session,
        installation_id: str,
        user_id: Optional[str],
        domain: str,
        privacy_minimized_path: str,
        timestamp: datetime,
    ) -> Visit:
        visit = (
            db.query(Visit)
            .filter(
                Visit.installation_id == installation_id,
                Visit.normalized_domain == domain,
                Visit.privacy_minimized_path == privacy_minimized_path,
            )
            .first()
        )

        if visit:
            visit.visit_count += 1
            visit.last_seen_at = timestamp
        else:
            visit = Visit(
                installation_id=installation_id,
                user_id=user_id,
                normalized_domain=domain,
                privacy_minimized_path=privacy_minimized_path,
                visit_count=1,
                first_seen_at=timestamp,
                last_seen_at=timestamp,
            )
            db.add(visit)

        return visit


event_service = EventService()

