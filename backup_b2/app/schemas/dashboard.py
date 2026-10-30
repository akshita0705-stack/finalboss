from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel


class TrendDay(BaseModel):
    date: str
    counts: Dict[str, int]  # keyed by status label (HIGH_RISK, SUSPICIOUS, ...)


class RecentFinding(BaseModel):
    id: str
    domain: str
    severity: str        # raw backend severity: low/medium/high/critical/unknown
    status_label: str    # mapped label: HIGH_RISK/SUSPICIOUS/NEEDS_REVIEW/LOW_OBSERVED_RISK/UNKNOWN
    risk_score: int
    status: str          # workflow state: active/investigating/resolved/false_positive
    explanation: str
    created_at: datetime


class RecentEvent(BaseModel):
    id: str
    domain: str
    event_type: str
    status_label: str
    created_at: datetime


class HealthItem(BaseModel):
    ok: bool
    label: str
    detail: str


class DashboardHealth(BaseModel):
    backend: HealthItem
    graph: HealthItem
    threat_provider: HealthItem


class DashboardSummary(BaseModel):
    installations_linked: int
    last_event_at: Optional[datetime] = None
    total_events: int
    total_findings: int
    open_findings: int
    status_counts: Dict[str, int]
    trend: List[TrendDay]
    recent_findings: List[RecentFinding]
    recent_events: List[RecentEvent]
    health: DashboardHealth
    limitations: str
