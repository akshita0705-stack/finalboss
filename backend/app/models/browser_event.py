from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, JSONBType, generate_uuid, utc_now


class BrowserEvent(Base):
    __tablename__ = "browser_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    installation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    normalized_domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    sanitized_url_path: Mapped[str] = mapped_column(Text, nullable=False)
    scheme: Mapped[str] = mapped_column(String(10), default="https", nullable=False)
    
    event_type: Mapped[str] = mapped_column(String(50), default="navigation", nullable=False)  # navigation, redirect, subresource
    source: Mapped[str] = mapped_column(String(50), default="chrome_extension", nullable=False)
    
    processing_status: Mapped[str] = mapped_column(
        String(50), default="received", nullable=False
    )  # received, assessed, enriched, failed
    
    preliminary_risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    preliminary_severity: Mapped[str] = mapped_column(String(20), default="low", nullable=False)  # low, medium, high, critical, unknown

    referrer_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    redirect_source_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("browser_events.id", ondelete="SET NULL"), nullable=True)
    redirect_chain: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONBType, default=list, nullable=True)
    
    # Redacted metadata (browser version, tab id, privacy-safe signals)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONBType, default=dict, nullable=True)

    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    findings: Mapped[List["SecurityFinding"]] = relationship("SecurityFinding", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_browser_events_inst_domain", "installation_id", "normalized_domain"),
        Index("ix_browser_events_created_at_desc", created_at.desc()),
    )

