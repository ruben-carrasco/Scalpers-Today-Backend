from dataclasses import dataclass
from typing import Any


@dataclass
class ExpoPushMessage:
    to: str  # Expo push token (ExponentPushToken[xxx])
    title: str
    body: str
    data: dict[str, Any] | None = None
    sound: str = "default"
    priority: str = "high"
    badge: int = 1

    def to_dict(self) -> dict[str, Any]:
        message = {
            "to": self.to,
            "title": self.title,
            "body": self.body,
            "sound": self.sound,
            "priority": self.priority,
            "badge": self.badge,
        }
        if self.data:
            message["data"] = self.data
        return message
