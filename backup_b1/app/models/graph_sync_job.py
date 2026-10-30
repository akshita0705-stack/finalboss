from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, JSONBType, generate_uuid, utc_now


class GraphSyncJob(Base):
    __tablename__ = "graph_sync_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # website, visit, finding, indicator, external_domain
    entity_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    operation: Mapped[str] = mapped_column(String(20), default="upsert", nullable=False)  # upsert, delete
    
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True, nullable=False)  # pending, processing, synced, failed, retrying
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONBType, default=dict, nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_graph_jobs_status_retry", "status", "next_retry_at"),
    )

