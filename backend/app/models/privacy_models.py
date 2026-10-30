from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String, Integer, Boolean, DateTime, ForeignKey, Index, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, JSONBType, generate_uuid, utc_now


class BrowserSession(Base):
    """One row per (user, browser installation). Only a HASH of the installation id is stored."""
    __tablename__ = "browser_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    installation_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 hex
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "installation_hash", name="uq_session_user_installation"),
    )


class ThreatLookup(Base):
    """Cache of reputation-provider results. 'no_match' is NOT the same as 'safe'."""
    __tablename__ = "threat_lookups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    # match | no_match | timeout | rate_limited | unavailable | error
    result_status: Mapped[str] = mapped_column(String(20), nullable=False)
    categories: Mapped[List[str]] = mapped_column(JSONBType, default=list, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_threat_lookups_domain_provider", "domain", "provider", "checked_at"),
        Index("ix_threat_lookups_expires", "expires_at"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("security_findings.id", ondelete="CASCADE"), nullable=False
    )
    # pending | delivered | failed | suppressed
    delivery_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "finding_id", name="uq_alert_user_finding"),  # dedup
        Index("ix_alerts_user_created", "user_id", "created_at"),
    )


class UserSetting(Base):
    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    excluded_domains: Mapped[List[str]] = mapped_column(JSONBType, default=list, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    notification_preferences: Mapped[Dict[str, Any]] = mapped_column(
        JSONBType, default=lambda: {"browser_notifications": True, "min_severity": "high"}, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    referenced_finding_ids: Mapped[List[str]] = mapped_column(JSONBType, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_investigations_user_created", "user_id", "created_at"),)