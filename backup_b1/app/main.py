from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect, Request, status
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.core.logging import logger
from app.db.base import Base
from app.db.session import engine, get_db
from app.api.deps import resolve_installation_ids_from_token
from app.api.routes import api_router, health
from app.services.notification_service import notification_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist in development / SQLite mode
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} ({settings.ENVIRONMENT})")
    try:
        # Create tables automatically for zero-friction local development if not already present
        Base.metadata.create_all(bind=engine)
        logger.info("Database schemas verified.")
    except Exception as e:
        logger.error(f"Database schema initialization warning: {e}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
# TraceGuard AI — Graph-Powered Browser Security Investigation Platform

TraceGuard AI monitors and analyzes browser navigation events, evaluates domain spoofing
and lookalike candidates, tracks repetition patterns, generates security findings,
and synchronizes investigation entities to a TigerGraph knowledge graph.

## Disclaimer
TraceGuard AI is an automated investigation telemetry and heuristic detection engine.
It is **not** a complete antivirus replacement and does not guarantee that unflagged websites are benign.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS: explicit origins only. Credentials are never combined with a wildcard.
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else []
_wildcard = "*" in origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=not _wildcard,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Installation-ID"],
    allow_origin_regex=r"chrome-extension://[a-z]{32}",
)

# Root liveness/readiness probes
app.include_router(health.router)

# Versioned API routes (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)


# Live WebSocket Endpoint for Real-Time Security Alerts (authenticated)
@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """
    Authenticated WebSocket. Connect with: ws://localhost:8000/ws/alerts?token=<JWT>
    The client only receives alerts for installations owned by the token's user.
    Browsers cannot set headers on WebSocket handshakes, so the short-lived JWT is passed as a
    query parameter; never log full request URLs for this endpoint.
    """
    installation_ids = resolve_installation_ids_from_token(db, token)
    if installation_ids is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    await notification_service.subscribe_websocket(websocket, installation_ids)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WebSocket connection terminated: {e}")
    finally:
        await notification_service.unsubscribe_websocket(websocket, installation_ids)


# Consistent Global Error Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": [{"loc": list(e.get("loc", [])), "msg": str(e.get("msg", "")), "type": str(e.get("type", ""))} for e in exc.errors()],
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred during request processing.",
        },
    )

