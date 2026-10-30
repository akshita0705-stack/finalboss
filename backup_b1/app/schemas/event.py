from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class NavigationEventCreate(BaseModel):
    url: str = Field(..., description="Target URL visited in the browser")
    event_type: str = Field(default="navigation", description="Event type: navigation, redirect, download")
    timestamp: Optional[datetime] = Field(default=None, description="ISO timestamp recorded by client")
    referrer_url: Optional[str] = Field(default=None, description="Optional referrer URL (will be sanitized)")
    idempotency_key: Optional[str] = Field(default=None, description="Client-provided idempotency key or hash")
    installation_id: Optional[str] = Field(default=None, description="Installation ID scope (if not in auth header)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Safe browser metadata (tab_id, transition)")


class PreliminaryAssessment(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    severity: str  # low, medium, high, critical, unknown
    confidence: str  # low, medium, high
    immediate_alert: bool
    explanation: str
    rules_triggered: List[str]


class EventIngestResponse(BaseModel):
    event_id: str
    idempotency_key: str
    status: str  # received, deduplicated
    is_duplicate: bool
    normalized_domain: str
    sanitized_url_path: str
    preliminary_assessment: PreliminaryAssessment
    timestamp: datetime


class BrowserEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idempotency_key: str
    installation_id: str
    normalized_domain: str
    sanitized_url_path: str
    scheme: str
    event_type: str
    source: str
    processing_status: str
    preliminary_risk_score: int
    preliminary_severity: str
    referrer_domain: Optional[str] = None
    redirect_chain: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    client_timestamp: datetime
