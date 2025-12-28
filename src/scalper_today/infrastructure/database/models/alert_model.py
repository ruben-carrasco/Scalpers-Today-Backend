from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AlertModel(Base):
    __tablename__ = "alerts"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # User relationship
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    # Alert metadata
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Conditions (stored as JSON string)
    conditions: Mapped[str] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Statistics
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Indexes
    __table_args__ = (Index("idx_user_status", "user_id", "status"),)
