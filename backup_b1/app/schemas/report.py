from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict


class ReportDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_type: str
    date_range_start: datetime
    date_range_end: datetime
    status: str
    summary_data: Dict[str, Any]
    error_message: Optional[str] = None
    created_at: datetime


class DailyActivityReportData(BaseModel):
    date: str
    total_navigation_events: int
    unique_domains_visited: int
    repeated_visits_count: int
    frequently_visited_domains: List[Dict[str, Any]]
    hourly_activity_distribution: List[Dict[str, Any]]
    chronological_activity_timeline: List[Dict[str, Any]]
    estimated_time_on_site: Dict[str, Any]
    estimation_limitations_disclaimer: str


class DailySecurityReportData(BaseModel):
    date: str
    total_findings: int
    findings_by_severity: Dict[str, int]
    findings_by_category: Dict[str, int]
    high_risk_and_suspicious_observations: List[Dict[str, Any]]
    lookalike_domain_candidates: List[Dict[str, Any]]
    observed_redirects_and_external_relationships: List[Dict[str, Any]]
    unknown_assessments_and_provider_failures: List[Dict[str, Any]]
    unresolved_findings: List[Dict[str, Any]]
    recommended_next_steps: List[str]
    graph_sync_failures_count: int
    security_limitations_disclaimer: str
