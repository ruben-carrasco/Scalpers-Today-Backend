from dataclasses import dataclass
from datetime import datetime
from typing import Set


@dataclass
class NotificationJob:
    event_id: str
    event_name: str
    event_time: datetime
    country: str
    currency: str
    importance: int
    user_ids: Set[str]
    notified: bool = False
