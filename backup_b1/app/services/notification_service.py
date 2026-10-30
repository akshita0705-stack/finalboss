import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket
from app.core.logging import logger


class NotificationService:
    """
    Manages live notification distribution to frontend clients and analyst consoles
    via WebSocket connections and SSE event streams.
    """

    def __init__(self):
        # Active WebSockets grouped by installation_id (or '*' for global analyst consoles)
        self.active_websockets: Dict[str, Set[WebSocket]] = {}
        # SSE Queues for streaming clients
        self.sse_queues: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def connect_websocket(self, websocket: WebSocket, installation_id: str = "*"):
        await websocket.accept()
        async with self._lock:
            if installation_id not in self.active_websockets:
                self.active_websockets[installation_id] = set()
            self.active_websockets[installation_id].add(websocket)
        logger.info(f"WebSocket client connected for scope '{installation_id}'")

    async def disconnect_websocket(self, websocket: WebSocket, installation_id: str = "*"):
        async with self._lock:
            if installation_id in self.active_websockets:
                self.active_websockets[installation_id].discard(websocket)
                if not self.active_websockets[installation_id]:
                    del self.active_websockets[installation_id]
        logger.info(f"WebSocket client disconnected from scope '{installation_id}'")

    async def broadcast_alert(
        self,
        event_type: str,
        payload: Dict[str, Any],
        installation_id: Optional[str] = None,
    ):
        """
        Broadcast alert to relevant clients:
        - Clients subscribed to the specific installation_id
        - Clients subscribed to global '*' scope (analyst dashboards)
        """
        message = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        msg_text = json.dumps(message)

        # 1. Distribute to WebSockets
        # Alerts are delivered ONLY to clients authenticated for this installation.
        # There is no global "*" scope, so one user can never receive another user's alerts.
        target_scopes = [installation_id] if installation_id and installation_id != "*" else []

        sockets_to_send: List[WebSocket] = []
        async with self._lock:
            for scope in target_scopes:
                if scope in self.active_websockets:
                    sockets_to_send.extend(list(self.active_websockets[scope]))

        for ws in sockets_to_send:
            try:
                await ws.send_text(msg_text)
            except Exception as e:
                logger.debug(f"Failed to send to WebSocket, will drop on disconnect: {e}")

        # 2. Distribute to SSE queues
        async with self._lock:
            for scope in target_scopes:
                if scope in self.sse_queues:
                    for queue in self.sse_queues[scope]:
                        try:
                            queue.put_nowait(msg_text)
                        except asyncio.QueueFull:
                            pass

    async def subscribe_websocket(self, websocket: WebSocket, installation_ids: List[str]):
        """Register an already-accepted, authenticated WebSocket for the given installations."""
        async with self._lock:
            for iid in installation_ids:
                self.active_websockets.setdefault(iid, set()).add(websocket)

    async def unsubscribe_websocket(self, websocket: WebSocket, installation_ids: List[str]):
        async with self._lock:
            for iid in installation_ids:
                if iid in self.active_websockets:
                    self.active_websockets[iid].discard(websocket)
                    if not self.active_websockets[iid]:
                        del self.active_websockets[iid]

    async def register_sse_client(self, installation_id: str = "*") -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            if installation_id not in self.sse_queues:
                self.sse_queues[installation_id] = []
            self.sse_queues[installation_id].append(queue)
        return queue

    async def unregister_sse_client(self, queue: asyncio.Queue, installation_id: str = "*"):
        async with self._lock:
            if installation_id in self.sse_queues:
                if queue in self.sse_queues[installation_id]:
                    self.sse_queues[installation_id].remove(queue)
                if not self.sse_queues[installation_id]:
                    del self.sse_queues[installation_id]


notification_service = NotificationService()

