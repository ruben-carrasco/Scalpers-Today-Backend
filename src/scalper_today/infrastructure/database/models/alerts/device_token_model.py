from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class DeviceTokenModel(Base):
    __tablename__ = "device_tokens"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # User relationship
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    # Device info
    token: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    device_type: Mapped[str] = mapped_column(String(20))
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Indexes
    __table_args__ = (Index("idx_user_active", "user_id", "is_active"),)
