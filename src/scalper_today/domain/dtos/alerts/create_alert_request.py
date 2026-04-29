from dataclasses import dataclass


@dataclass
class CreateAlertRequest:
    user_id: str
    name: str
    description: str | None = None
    conditions: list[dict] = None
    push_enabled: bool = True
