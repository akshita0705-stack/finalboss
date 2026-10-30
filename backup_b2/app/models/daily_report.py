from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, JSONBType, generate_uuid, utc_now


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    installation_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # activity, security
    
    date_range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date_range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    summary_data: Mapped[Dict[str, Any]] = mapped_column(JSONBType, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="completed", nullable=False)  # pending, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    __table_args__ = (
        Index("ix_daily_reports_type_dates", "report_type", "date_range_start", "date_range_end"),
    )

