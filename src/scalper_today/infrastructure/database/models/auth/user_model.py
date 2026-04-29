from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class UserModel(Base):
    __tablename__ = "users"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    # Profile
    name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Preferences (stored as JSON string)
    preferences: Mapped[str] = mapped_column(
        Text, default='{"language": "es", "currency": "usd", "timezone": "Europe/Madrid"}'
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Index for active users lookup
    __table_args__ = (Index("idx_email_active", "email", "is_active"),)
