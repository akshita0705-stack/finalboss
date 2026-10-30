import pytest
from app.models.browser_event import BrowserEvent
from app.models.user import User
from app.db.base import utc_now


def test_duplicate_registration_rejected(client):
    payload = {
        "email": "unique_user@traceguard.ai",
        "password": "Password123!Secure",
        "full_name": "Unique Analyst",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_invalid_login_credentials(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@traceguard.ai", "password": "wrongpassword"},
    )
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


def test_unauthenticated_protected_endpoint(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_installation_data_isolation(client, db_session):
    now = utc_now()

    # Create event for Installation A
    ev_a = BrowserEvent(
        idempotency_key="iso-a-1",
        installation_id="install-alpha",
        normalized_domain="alpha-internal.org",
        sanitized_url_path="/confidential",
        event_type="navigation",
        preliminary_risk_score=0,
        preliminary_severity="low",
        client_timestamp=now,
        created_at=now,
    )
    # Create event for Installation B
    ev_b = BrowserEvent(
        idempotency_key="iso-b-1",
        installation_id="install-beta",
        normalized_domain="beta-internal.org",
        sanitized_url_path="/private",
        event_type="navigation",
        preliminary_risk_score=0,
        preliminary_severity="low",
        client_timestamp=now,
        created_at=now,
    )
    db_session.add_all([ev_a, ev_b])
    db_session.commit()

    from conftest import make_user_headers
    headers_a = make_user_headers(db_session, "alpha@example.com", "install-alpha")
    headers_b = make_user_headers(db_session, "beta@example.com", "install-beta")

    # Each user sees only the installation they own; a client-supplied installation_id is ignored
    res_a = client.get("/api/v1/activity?installation_id=install-beta", headers=headers_a)
    assert res_a.status_code == 200
    domains_a = [t["domain"] for t in res_a.json()["recent_timeline"]]
    assert "alpha-internal.org" in domains_a
    assert "beta-internal.org" not in domains_a

    res_b = client.get("/api/v1/activity", headers=headers_b)
    assert res_b.status_code == 200
    domains_b = [t["domain"] for t in res_b.json()["recent_timeline"]]
    assert "beta-internal.org" in domains_b
    assert "alpha-internal.org" not in domains_b

