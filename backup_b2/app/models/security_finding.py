from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, JSONBType, generate_uuid, utc_now


class SecurityFinding(Base):
    __tablename__ = "security_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("browser_events.id", ondelete="CASCADE"), nullable=True, index=True)
    installation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    category: Mapped[str] = mapped_column(String(50), nullable=False)  # phishing, homograph, deceptive_structure, redirect_anomaly, threat_intel, malware
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical, unknown
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)   # 0 to 100
    
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)  # active, investigating, resolved, false_positive
    confidence: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low, medium, high
    
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_source: Mapped[str] = mapped_column(String(100), default="deterministic_engine", nullable=False)
    
    # Structured evidence: rule triggers, signals, domain similarity candidate, diff, provider details
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    event: Mapped[Optional["BrowserEvent"]] = relationship("BrowserEvent", back_populates="findings")

    __table_args__ = (
        Index("ix_findings_severity_status", "severity", "status"),
        Index("ix_findings_inst_created", "installation_id", "created_at"),
    )

