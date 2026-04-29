from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class DeviceToken:
    id: str
    user_id: str
    token: str
    device_type: str = "unknown"
    device_name: str = "unknown"
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(UTC))
