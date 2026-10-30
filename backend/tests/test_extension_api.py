from app.core.config import settings
from app.core.security import hash_api_key
from app.models.user import ApiKey
from app.services.status_labels import STATUS_LABELS


def _event(event_id="evt-0001-aaaa", hostname="example.com", **extra):
    return {"event_id": event_id, "hostname": hostname, "event_type": "navigation", **extra}


def test_extension_event_returns_status_label(client, extension_auth_headers):
    res = client.post("/api/v1/extension/events", json=_event(), headers=extension_auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["assessment"]["severity"] in STATUS_LABELS
    assert body["assessment"]["evidence_quality"]  # always states how good the evidence is


def test_extension_event_is_idempotent(client, extension_auth_headers):
    first = client.post("/api/v1/extension/events", json=_event("evt-dup-0001"), headers=extension_auth_headers)
    second = client.post("/api/v1/extension/events", json=_event("evt-dup-0001"), headers=extension_auth_headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["is_duplicate"] is False
    assert second.json()["is_duplicate"] is True
    assert first.json()["event_id"] == second.json()["event_id"]


def test_extension_rejects_url_like_hostname(client, extension_auth_headers):
    for bad in ["example.com/login?token=abc", "user:pw@example.com", "exa mple.com", "example.com#frag"]:
        res = client.post("/api/v1/extension/events", json=_event(hostname=bad), headers=extension_auth_headers)
        assert res.status_code == 422, bad


def test_extension_requires_authentication(client):
    res = client.post("/api/v1/extension/events", json=_event())
    assert res.status_code == 401


def test_extension_accepts_api_key_as_bearer(client, db_session):
    db_session.add(ApiKey(installation_id="inst-bearer-1", hashed_key=hash_api_key("tg_live_key_abc"), name="t"))
    db_session.commit()
    res = client.post(
        "/api/v1/extension/events",
        json=_event("evt-bearer-01"),
        headers={"Authorization": "Bearer tg_live_key_abc"},
    )
    assert res.status_code == 200


def test_dev_key_disabled_in_production(client, extension_auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DEBUG", False)
    res = client.post("/api/v1/extension/events", json=_event("evt-prod-0001"), headers=extension_auth_headers)
    assert res.status_code == 401


def test_extension_status(client, extension_auth_headers):
    res = client.get("/api/v1/extension/status", headers=extension_auth_headers)
    assert res.status_code == 200
    assert res.json()["backend"] == "connected"
