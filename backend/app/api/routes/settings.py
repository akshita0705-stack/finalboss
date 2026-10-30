from fastapi import APIRouter, Depends, status
from app.models.user import User
from app.core.config import settings
from app.schemas.settings import SystemSettingsResponse, SystemSettingsUpdate
from app.api.deps import require_role

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get("", response_model=SystemSettingsResponse)
def get_system_settings():
    """Retrieve active system configurations and risk thresholds."""
    return SystemSettingsResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        data_retention_days=settings.DATA_RETENTION_DAYS,
        rate_limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        threat_intel_enabled=settings.THREAT_INTEL_ENABLED,
        threat_intel_provider=settings.THREAT_INTEL_PROVIDER,
        tigergraph_enabled=settings.TIGERGRAPH_ENABLED,
        tigergraph_use_mock=settings.TIGERGRAPH_USE_MOCK,
        llm_enabled=settings.LLM_ENABLED,
        llm_provider=settings.LLM_PROVIDER,
        risk_thresholds={
            "low": settings.RISK_THRESHOLD_LOW,
            "medium": settings.RISK_THRESHOLD_MEDIUM,
            "high": settings.RISK_THRESHOLD_HIGH,
            "critical": settings.RISK_THRESHOLD_CRITICAL,
        },
    )


@router.put("", response_model=SystemSettingsResponse)
def update_system_settings(
    updates: SystemSettingsUpdate,
    _admin: User = Depends(require_role(["admin"])),
):
    """Update process-wide runtime settings. Admin only (these are global, not per-user)."""
    if updates.data_retention_days is not None:
        settings.DATA_RETENTION_DAYS = updates.data_retention_days
    if updates.threat_intel_enabled is not None:
        settings.THREAT_INTEL_ENABLED = updates.threat_intel_enabled
    if updates.threat_intel_provider is not None:
        settings.THREAT_INTEL_PROVIDER = updates.threat_intel_provider
    if updates.tigergraph_use_mock is not None:
        settings.TIGERGRAPH_USE_MOCK = updates.tigergraph_use_mock
    if updates.risk_threshold_low is not None:
        settings.RISK_THRESHOLD_LOW = updates.risk_threshold_low
    if updates.risk_threshold_medium is not None:
        settings.RISK_THRESHOLD_MEDIUM = updates.risk_threshold_medium
    if updates.risk_threshold_high is not None:
        settings.RISK_THRESHOLD_HIGH = updates.risk_threshold_high
    if updates.risk_threshold_critical is not None:
        settings.RISK_THRESHOLD_CRITICAL = updates.risk_threshold_critical

    return get_system_settings()

