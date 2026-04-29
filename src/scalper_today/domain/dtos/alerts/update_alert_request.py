from dataclasses import dataclass


@dataclass
class UpdateAlertRequest:
    alert_id: str
    user_id: str
    name: str | None = None
    description: str | None = None
    conditions: list[dict] | None = None
    status: str | None = None
    push_enabled: bool | None = None
