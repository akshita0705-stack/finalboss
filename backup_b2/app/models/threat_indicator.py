from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, JSONBType, generate_uuid, utc_now


class ThreatIndicator(Base):
    __tablename__ = "threat_indicators"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    indicator_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # domain, url, ip, hash
    normalized_value: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    
    provider: Mapped[str] = mapped_column(String(100), index=True, nullable=False)  # google_safebrowsing, mock_threat_intel, local_feed
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)  # clean, suspicious, malicious, unknown
    confidence: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low, medium, high
    
    response_status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)  # success, error, rate_limited, disabled
    raw_details: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_indicator_provider_val", "provider", "normalized_value"),
    )

