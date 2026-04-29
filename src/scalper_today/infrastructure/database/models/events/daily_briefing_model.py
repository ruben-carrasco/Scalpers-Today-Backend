from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class DailyBriefingModel(Base):
    __tablename__ = "daily_briefings"

    # Primary key (date-based)
    date: Mapped[datetime] = mapped_column(DateTime, primary_key=True)

    # Briefing content
    general_outlook: Mapped[str] = mapped_column(Text)
    impacted_assets: Mapped[str] = mapped_column(String(1000))
    cautionary_hours: Mapped[str] = mapped_column(String(1000))

    # Statistics
    sentiment: Mapped[str] = mapped_column(String(20))
    volatility_level: Mapped[str] = mapped_column(String(20))
    total_events: Mapped[int] = mapped_column(Integer, default=0)
    high_impact_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
