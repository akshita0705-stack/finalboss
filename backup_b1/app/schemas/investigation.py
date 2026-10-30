from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class InvestigationRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Analyst investigation question")
    domain: Optional[str] = Field(None, description="Optional target domain to scope investigation")
    finding_id: Optional[str] = Field(None, description="Optional finding ID to investigate")
    max_evidence_items: int = Field(default=10, ge=1, le=50)


class EvidenceCitation(BaseModel):
    source_type: str  # finding, event, threat_indicator, graph_relation
    id: str
    summary: str
    timestamp: Optional[datetime] = None
    confidence: str = "medium"
    is_inferred: bool = False


class InvestigationResponse(BaseModel):
    question: str
    answer: str
    target_domain: Optional[str] = None
    confidence: str  # high, medium, low
    supporting_evidence: List[EvidenceCitation]
    cited_finding_ids: List[str]
    cited_event_ids: List[str]
    observed_facts: List[str]
    inferred_relationships: List[str]
    unknown_information: List[str]
    limitations: str
    llm_provider_used: str  # "gemini", "openai", or "evidence_fallback"
    timestamp: datetime

