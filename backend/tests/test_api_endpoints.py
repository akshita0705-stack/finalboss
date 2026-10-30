import pytest


def test_health_and_readiness_endpoints(client):
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["database"]["connected"] is True


def test_auth_workflow_and_api_keys(client):
    # Register new user
    res_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "analyst_new@traceguard.ai",
            "password": "Password123!Secure",
            "full_name": "New Analyst",
            "role": "analyst",
        },
    )
    assert res_reg.status_code == 201
    assert res_reg.json()["email"] == "analyst_new@traceguard.ai"

    # Login
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst_new@traceguard.ai", "password": "Password123!Secure"},
    )
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    assert token is not None

    headers = {"Authorization": f"Bearer {token}"}

    # /auth/me
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "analyst_new@traceguard.ai"

    # Create Extension API Key
    res_key = client.post(
        "/api/v1/auth/api-keys",
        headers=headers,
        json={"name": "Chrome Extension Lab", "installation_id": "inst-lab-101"},
    )
    assert res_key.status_code == 201
    assert "api_key" in res_key.json()
    assert res_key.json()["api_key"].startswith("tg_ext_")


def test_post_event_with_extension_key(client, extension_auth_headers, linked_admin_headers):
    payload = {
        "url": "https://fastapi.tiangolo.com/tutorial/",
        "event_type": "navigation",
        "idempotency_key": "api-test-key-001",
    }
    res = client.post("/api/v1/events", headers=extension_auth_headers, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["normalized_domain"] == "tiangolo.com"
    assert data["is_duplicate"] is False
    assert data["preliminary_assessment"]["risk_score"] == 0

    # List events
    res_list = client.get("/api/v1/events?domain=tiangolo.com", headers=linked_admin_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_findings_workflow(client, extension_auth_headers, linked_admin_headers):
    # Post a suspicious event to generate a finding
    payload = {
        "url": "http://apple-support-verify.phishingsite.top/login",
        "event_type": "navigation",
        "idempotency_key": "phish-test-key-555",
    }
    client.post("/api/v1/events", headers=extension_auth_headers, json=payload)

    # Query findings
    res_findings = client.get("/api/v1/findings?domain=phishingsite.top", headers=linked_admin_headers)
    assert res_findings.status_code == 200
    findings = res_findings.json()
    assert len(findings) >= 1
    finding_id = findings[0]["id"]

    # Retrieve finding detail
    res_detail = client.get(f"/api/v1/findings/{finding_id}", headers=linked_admin_headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == finding_id

    # Update finding status
    res_update = client.patch(
        f"/api/v1/findings/{finding_id}",
        headers=linked_admin_headers,
        json={"status": "resolved"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "resolved"


def test_activity_and_graph_apis(client, admin_auth_headers):
    # Test activity
    res_act = client.get("/api/v1/activity?days=7", headers=admin_auth_headers)
    assert res_act.status_code == 200
    assert "total_events" in res_act.json()
    assert "unique_domains" in res_act.json()

    # Test graph relationships
    res_graph = client.get("/api/v1/graph/relationships")
    assert res_graph.status_code == 200
    assert "nodes" in res_graph.json()
    assert "edges" in res_graph.json()

    # Test graph status
    res_status = client.get("/api/v1/graph/status")
    assert res_status.status_code == 200
    assert "provider" in res_status.json()


def test_settings_api(client, admin_auth_headers):
    res_get = client.get("/api/v1/settings")
    assert res_get.status_code == 200
    assert res_get.json()["app_name"] == "TraceGuard AI"

    # Unauthenticated callers must not be able to change global settings
    assert client.put("/api/v1/settings", json={"data_retention_days": 60}).status_code == 401

    # Admin can update retention days
    res_put = client.put("/api/v1/settings", json={"data_retention_days": 60}, headers=admin_auth_headers)
    assert res_put.status_code == 200
    assert res_put.json()["data_retention_days"] == 60

