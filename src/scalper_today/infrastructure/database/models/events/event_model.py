from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class EventModel(Base):
    __tablename__ = "economic_events"

    # Primary key
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Event metadata
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    time: Mapped[str] = mapped_column(String(10))

    # Event details
    title: Mapped[str] = mapped_column(String(500))
    country: Mapped[str] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(10))
    importance: Mapped[int] = mapped_column(Integer, index=True)

    # Economic data
    actual: Mapped[str] = mapped_column(String(100), default="")
    forecast: Mapped[str] = mapped_column(String(100), default="")
    previous: Mapped[str] = mapped_column(String(100), default="")
    surprise: Mapped[str] = mapped_column(String(20), default="neutral")

    # Source
    url: Mapped[str] = mapped_column(String(500), default="")

    # AI Analysis - Quick (all events)
    quick_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quick_impact: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    quick_sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # AI Analysis - Deep (high-impact only)
    deep_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    macro_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technical_levels: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trading_strategies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impacted_assets: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Analysis status tracking
    has_quick_analysis: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    has_deep_analysis: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_date_importance", "date", "importance"),
        Index("idx_analysis_status", "date", "has_quick_analysis", "has_deep_analysis"),
    )
