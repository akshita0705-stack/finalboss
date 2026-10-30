from typing import Optional, Dict
from pydantic import BaseModel


class SystemSettingsResponse(BaseModel):
    app_name: str
    app_version: str
    environment: str
    debug: bool
    data_retention_days: int
    rate_limit_per_minute: int
    threat_intel_enabled: bool
    threat_intel_provider: str
    tigergraph_enabled: bool
    tigergraph_use_mock: bool
    llm_enabled: bool
    llm_provider: str
    risk_thresholds: Dict[str, int]


class SystemSettingsUpdate(BaseModel):
    data_retention_days: Optional[int] = None
    threat_intel_enabled: Optional[bool] = None
    threat_intel_provider: Optional[str] = None
    tigergraph_use_mock: Optional[bool] = None
    risk_threshold_low: Optional[int] = None
    risk_threshold_medium: Optional[int] = None
    risk_threshold_high: Optional[int] = None
    risk_threshold_critical: Optional[int] = None

