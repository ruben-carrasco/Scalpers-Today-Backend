from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .user_preferences import UserPreferences


@dataclass
class User:
    id: str
    email: str
    name: str
    hashed_password: str
    avatar_url: Optional[str] = None
    preferences: UserPreferences = field(default_factory=UserPreferences)
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
