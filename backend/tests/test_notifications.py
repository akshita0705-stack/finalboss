import pytest
from app.services.notification_service import notification_service
from conftest import make_user_headers


@pytest.mark.asyncio
async def test_notification_service_sse_dispatch():
    # Register SSE queue
    queue = await notification_service.register_sse_client(installation_id="test-client-99")
    try:
        # Broadcast alert
        await notification_service.broadcast_alert(
            event_type="SECURITY_ALERT",
            payload={"domain": "alert-test.com", "severity": "high"},
            installation_id="test-client-99",
        )

        # Retrieve message from queue
        msg = queue.get_nowait()
        assert "SECURITY_ALERT" in msg
        assert "alert-test.com" in msg
    finally:
        await notification_service.unregister_sse_client(queue, installation_id="test-client-99")


def test_websocket_alerts_endpoint(client, db_session):
    headers = make_user_headers(db_session, "ws-user@example.com", installation_id="test-ws-01")
    token = headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/ws/alerts?token={token}") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert '{"type": "pong"}' in data


def test_websocket_rejects_unauthenticated(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/alerts?installation_id=*"):
            pass


def test_sse_requires_token(client):
    assert client.get("/api/v1/stream").status_code == 401
    assert client.get("/api/v1/stream?token=not-a-jwt").status_code == 401


@pytest.mark.asyncio
async def test_alerts_are_not_delivered_to_other_installations():
    mine = await notification_service.register_sse_client(installation_id="inst-mine")
    other = await notification_service.register_sse_client(installation_id="inst-other")
    try:
        await notification_service.broadcast_alert("SECURITY_ALERT", {"domain": "x.test"}, installation_id="inst-mine")
        assert not mine.empty()
        assert other.empty()
    finally:
        await notification_service.unregister_sse_client(mine, "inst-mine")
        await notification_service.unregister_sse_client(other, "inst-other")

