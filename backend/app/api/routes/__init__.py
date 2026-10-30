from fastapi import APIRouter
from app.api.routes import (
    health, auth, events, findings, activity, reports, graph,
    investigations, settings, stream, dashboard, extension, user_settings, privacy,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(findings.router)
api_router.include_router(activity.router)
api_router.include_router(reports.router)
api_router.include_router(graph.router)
api_router.include_router(investigations.router)
api_router.include_router(settings.router)
api_router.include_router(user_settings.router)
api_router.include_router(privacy.router)
api_router.include_router(stream.router)
api_router.include_router(dashboard.router)
api_router.include_router(extension.router)

__all__ = ["api_router"]