import pytest
from app.agents.investigation_agent import investigation_agent
from app.schemas.investigation import InvestigationRequest
from app.models.security_finding import SecurityFinding
from app.db.base import utc_now


def test_investigation_agent_grounded_evidence(db_session):
    now = utc_now()
    finding = SecurityFinding(
        installation_id="test-inst",
        domain="target-phish.com",
        category="homograph",
        severity="high",
        risk_score=85,
        status="active",
        confidence="high",
        explanation="Lookalike candidate for 'paypal.com'",
        rule_id="RULE_LOOKALIKE_DOMAIN",
        evidence={
            "lookalike_candidate": {
                "target_domain": "paypal.com",
                "similarity_score": 0.89,
                "edit_distance": 1,
            }
        },
        created_at=now,
    )
    db_session.add(finding)
    db_session.commit()

    req = InvestigationRequest(
        question="Is target-phish.com suspicious or safe?",
        domain="target-phish.com",
    )
    res = investigation_agent.investigate(db_session, req)

    assert res.target_domain == "target-phish.com"
    assert res.confidence == "high"
    assert finding.id in res.cited_finding_ids
    assert len(res.observed_facts) >= 1
    assert len(res.inferred_relationships) >= 1
    assert "paypal.com" in res.inferred_relationships[0]
    assert res.llm_provider_used == "evidence_fallback"
    assert "TraceGuard AI analysis is strictly restricted" in res.limitations


def test_investigation_agent_unknown_destination(db_session):
    req = InvestigationRequest(
        question="What is the reputation of completely-unknown-domain-999.org?",
        domain="completely-unknown-domain-999.org",
    )
    res = investigation_agent.investigate(db_session, req)
    assert res.confidence == "low"
    assert len(res.unknown_information) >= 1
    assert "No previous security findings" in res.unknown_information[0]
    assert "insufficient evidence" in res.answer.lower()

