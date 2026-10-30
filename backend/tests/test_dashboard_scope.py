from conftest import make_user_headers
from app.models.browser_event import BrowserEvent
from app.models.security_finding import SecurityFinding

PROTECTED = [
    "/api/v1/dashboard/summary",
    "/api/v1/findings",
    "/api/v1/events",
    "/api/v1/activity",
    "/api/v1/activity/visits",
    "/api/v1/reports/security/daily",
    "/api/v1/reports/activity/daily",
]


def _finding(db, inst, domain, severity, score=50):
    f = SecurityFinding(
        installation_id=inst, domain=domain, category="phishing", severity=severity,
        risk_score=score, explanation=f"test {severity}", rule_id="TEST",
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def test_protected_endpoints_require_login(client):
    for path in PROTECTED:
        assert client.get(path).status_code == 401, path


def test_user_without_linked_installation_sees_nothing(client, db_session):
    h = make_user_headers(db_session, "nolink@example.com")
    _finding(db_session, "someone-elses-install", "secret.example.test", "critical")
    assert client.get("/api/v1/findings", headers=h).json() == []
    s = client.get("/api/v1/dashboard/summary", headers=h).json()
    assert s["installations_linked"] == 0
    assert s["total_findings"] == 0
    assert s["recent_findings"] == []


def test_finding_access_is_limited_to_owner(client, db_session):
    ha = make_user_headers(db_session, "a@example.com", "inst-a")
    hb = make_user_headers(db_session, "b@example.com", "inst-b")
    fa = _finding(db_session, "inst-a", "a-only.example.test", "high")

    assert client.get(f"/api/v1/findings/{fa.id}", headers=ha).status_code == 200
    assert client.get(f"/api/v1/findings/{fa.id}", headers=hb).status_code == 404
    assert client.patch(f"/api/v1/findings/{fa.id}", headers=hb, json={"status": "resolved"}).status_code == 404
    assert [f["domain"] for f in client.get("/api/v1/findings", headers=hb).json()] == []


def test_dashboard_summary_maps_statuses_and_scopes(client, db_session):
    ha = make_user_headers(db_session, "sum-a@example.com", "inst-sum-a")
    for sev in ("critical", "high", "medium", "low", "unknown"):
        _finding(db_session, "inst-sum-a", f"{sev}.example.test", sev)
    _finding(db_session, "inst-other", "other.example.test", "critical")  # must not be counted
    db_session.add(BrowserEvent(
        idempotency_key="sum-ev-1", installation_id="inst-sum-a", normalized_domain="news.example.test",
        sanitized_url_path="/", event_type="navigation", preliminary_severity="low",
    ))
    db_session.commit()

    s = client.get("/api/v1/dashboard/summary?days=7", headers=ha).json()
    assert s["installations_linked"] == 1
    assert s["status_counts"] == {
        "HIGH_RISK": 1, "SUSPICIOUS": 1, "NEEDS_REVIEW": 1, "LOW_OBSERVED_RISK": 1, "UNKNOWN": 1,
    }
    assert s["total_findings"] == 5
    assert s["total_events"] == 1
    assert len(s["trend"]) == 7
    assert {f["domain"] for f in s["recent_findings"]} == {f"{x}.example.test" for x in ("critical", "high", "medium", "low", "unknown")}
    assert set(s["health"]) == {"backend", "graph", "threat_provider"}
    assert "not a safe verdict" in s["limitations"]


def test_security_report_is_scoped_to_user(client, db_session):
    ha = make_user_headers(db_session, "rep-a@example.com", "inst-rep-a")
    _finding(db_session, "inst-rep-a", "mine.example.test", "high")
    _finding(db_session, "inst-rep-zzz", "theirs.example.test", "high")
    r = client.get("/api/v1/reports/security/daily", headers=ha).json()
    assert r["total_findings"] == 1
