from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SecurityFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: Optional[str] = None
    installation_id: str
    domain: str
    category: str
    severity: str  # low, medium, high, critical, unknown
    risk_score: int
    status: str    # active, investigating, resolved, false_positive
    confidence: str
    explanation: str
    rule_id: str
    provider_source: str
    evidence: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SecurityFindingUpdate(BaseModel):
    status: str = Field(..., description="Updated status: active, investigating, resolved, false_positive")
