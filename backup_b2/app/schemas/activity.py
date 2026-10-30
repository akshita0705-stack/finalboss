from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict


class VisitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    normalized_domain: str
    privacy_minimized_path: str
    visit_count: int
    first_seen_at: datetime
    last_seen_at: datetime


class ActivityTimelineItem(BaseModel):
    id: str
    timestamp: datetime
    domain: str
    event_type: str
    risk_score: int
    severity: str
    has_finding: bool
    finding_id: Optional[str] = None


class DomainVisitStats(BaseModel):
    domain: str
    visit_count: int
    last_seen_at: datetime
    highest_risk_score: int
    severity: str


class HourlyDistributionItem(BaseModel):
    hour: int
    count: int


class ActivityAnalyticsResponse(BaseModel):
    total_events: int
    unique_domains: int
    repeated_visits_count: int
    top_domains: List[DomainVisitStats]
    hourly_distribution: List[HourlyDistributionItem]
    recent_timeline: List[ActivityTimelineItem]
