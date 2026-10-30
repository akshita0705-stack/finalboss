import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.schemas.investigation import InvestigationRequest, InvestigationResponse, EvidenceCitation
from app.agents.evidence_tools import EvidenceRetrievalTools
from app.db.base import utc_now


class InvestigationAgent:
    """
    Evidence-grounded AI security investigation agent.
    Grounds all analysis exclusively in observed telemetry and threat findings.
    Never hallucinates threats or fabricates evidence.
    """

    def investigate(self, db: Session, req: InvestigationRequest) -> InvestigationResponse:
        # 1. Determine target domain or finding ID
        target_domain = req.domain
        if not target_domain:
            target_domain = self._extract_domain_from_question(req.question)

        finding_details = None
        if req.finding_id:
            finding_details = EvidenceRetrievalTools.get_finding_by_id(db, req.finding_id)
            if finding_details and not target_domain:
                target_domain = finding_details["domain"]

        # 2. Gather Evidence
        evidence_citations: List[EvidenceCitation] = []
        cited_findings: List[str] = []
        cited_events: List[str] = []
        observed_facts: List[str] = []
        inferred_relationships: List[str] = []
        unknown_information: List[str] = []

        domain_evidence = None
        if target_domain:
            domain_evidence = EvidenceRetrievalTools.get_domain_evidence(db, target_domain)

        # 3. Process Findings Evidence
        if domain_evidence and domain_evidence["findings"]:
            for f in domain_evidence["findings"]:
                cited_findings.append(f["finding_id"])
                observed_facts.append(
                    f"Security finding '{f['finding_id']}' recorded with severity '{f['severity']}' (risk score {f['risk_score']}) under rule '{f['rule_id']}'."
                )
                evidence_citations.append(
                    EvidenceCitation(
                        source_type="finding",
                        id=f["finding_id"],
                        summary=f"{f['category'].upper()} finding: {f['explanation']}",
                        timestamp=datetime.fromisoformat(f["created_at"]),
                        confidence=f["confidence"],
                        is_inferred=False,
                    )
                )

                # Check if evidence contains lookalike or inferred relationships
                lookalike = f["evidence"].get("lookalike_candidate")
                if lookalike:
                    inferred_relationships.append(
                        f"Domain '{target_domain}' inferred as potential lookalike candidate for legitimate domain '{lookalike.get('target_domain')}' with edit distance {lookalike.get('edit_distance')}."
                    )

        if domain_evidence and domain_evidence["recent_events"]:
            for ev in domain_evidence["recent_events"]:
                cited_events.append(ev["event_id"])
                observed_facts.append(
                    f"Browser event '{ev['event_id']}' observed navigation to '{ev['sanitized_url']}' at {ev['timestamp']}."
                )

        if domain_evidence and domain_evidence["threat_indicators"]:
            for ind in domain_evidence["threat_indicators"]:
                observed_facts.append(
                    f"Threat intelligence feed '{ind['provider']}' returned verdict '{ind['verdict']}' (status: {ind['response_status']})."
                )

        # Identify missing or unknown telemetry
        if not domain_evidence or not domain_evidence["findings"]:
            unknown_information.append(
                f"No previous security findings or known threat intelligence records currently stored for '{target_domain or 'target'}'."
            )

        if not domain_evidence or domain_evidence["total_visits"] == 0:
            unknown_information.append("No historical navigation visits recorded in local telemetry.")

        # 4. Generate Synthesized Response
        llm_used = "evidence_fallback"
        answer, confidence = self._generate_grounded_answer(
            question=req.question,
            target_domain=target_domain,
            finding_details=finding_details,
            observed_facts=observed_facts,
            inferred_relationships=inferred_relationships,
            unknown_information=unknown_information,
        )

        limitations_msg = (
            "TraceGuard AI analysis is strictly restricted to locally recorded browser navigation events, "
            "deterministic heuristics, and authorized threat intelligence feeds. It does not replace full endpoint protection "
            "or guarantee that an unflagged domain is benign."
        )

        return InvestigationResponse(
            question=req.question,
            answer=answer,
            target_domain=target_domain,
            confidence=confidence,
            supporting_evidence=evidence_citations,
            cited_finding_ids=cited_findings,
            cited_event_ids=cited_events,
            observed_facts=observed_facts,
            inferred_relationships=inferred_relationships,
            unknown_information=unknown_information,
            limitations=limitations_msg,
            llm_provider_used=llm_used,
            timestamp=utc_now(),
        )

    def _extract_domain_from_question(self, question: str) -> Optional[str]:
        # Simple regex match for domains in question string
        match = re.search(r"([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}", question)
        if match:
            return match.group(0).lower()
        return None

    def _generate_grounded_answer(
        self,
        question: str,
        target_domain: Optional[str],
        finding_details: Optional[Dict[str, Any]],
        observed_facts: List[str],
        inferred_relationships: List[str],
        unknown_information: List[str],
    ) -> (str, str):
        if not target_domain and not finding_details and not observed_facts:
            return (
                "Insufficient evidence available. Please specify a target domain or finding ID to investigate.",
                "low",
            )

        paragraphs = []
        confidence = "medium"

        if target_domain:
            paragraphs.append(f"**Investigation Summary for `{target_domain}`**:")
        else:
            paragraphs.append("**Investigation Summary**:")

        if observed_facts:
            paragraphs.append("**Observed Facts & Telemetry**:")
            for fact in observed_facts[:5]:
                paragraphs.append(f"- {fact}")
            confidence = "high"
        else:
            paragraphs.append("- No confirmed security incidents or malicious indicators exist in the repository.")
            confidence = "low"

        if inferred_relationships:
            paragraphs.append("\n**Inferred Relationships (Subject to Verification)**:")
            for inf in inferred_relationships:
                paragraphs.append(f"- {inf}")

        if unknown_information:
            paragraphs.append("\n**Unknown / Missing Information**:")
            for unk in unknown_information:
                paragraphs.append(f"- {unk}")

        if observed_facts:
            paragraphs.append(
                f"\n**Conclusion**: Based solely on stored evidence, `{target_domain}` has associated security findings "
                "or elevated heuristics. Review the cited finding IDs and evidence signals prior to taking containment action."
            )
        else:
            paragraphs.append(
                f"\n**Conclusion**: There is currently insufficient evidence to designate `{target_domain or 'target'}` as malicious. "
                "Further navigation telemetry or external threat intelligence confirmation is required."
            )

        return "\n".join(paragraphs), confidence


investigation_agent = InvestigationAgent()

