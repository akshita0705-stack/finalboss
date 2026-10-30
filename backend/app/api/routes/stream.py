import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import resolve_installation_ids_from_token
from app.core.logging import logger
from app.db.session import get_db
from app.services.notification_service import notification_service

router = APIRouter(tags=["Live Stream & WebSockets"])


@router.get("/stream")
async def stream_live_alerts(
    request: Request,
    token: Optional[str] = Query(None, description="JWT access token (EventSource cannot send headers)"),
    db: Session = Depends(get_db),
):
    """
    Authenticated Server-Sent Events stream. Only alerts for installations owned by the
    token's user are delivered. Invalid or missing tokens receive 401.
    """
    installation_ids = resolve_installation_ids_from_token(db, token)
    if installation_ids is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing token")

    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    async with notification_service._lock:
        for iid in installation_ids:
            notification_service.sse_queues.setdefault(iid, []).append(queue)

    async def event_generator():
        try:
            yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: alert\ndata: {message}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive-ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            for iid in installation_ids:
                await notification_service.unregister_sse_client(queue, iid)
            logger.info("SSE client disconnected")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
