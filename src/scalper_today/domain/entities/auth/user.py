from dataclasses import dataclass, field
from datetime import UTC, datetime

from .user_preferences import UserPreferences


@dataclass
class User:
    id: str
    email: str
    name: str
    hashed_password: str
    avatar_url: str | None = None
    preferences: UserPreferences = field(default_factory=UserPreferences)
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
