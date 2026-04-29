from dataclasses import dataclass, field
from datetime import UTC, datetime

from .alert_condition import AlertCondition
from .alert_status import AlertStatus


@dataclass
class Alert:
    id: str
    user_id: str
    name: str
    description: str | None = None
    conditions: list[AlertCondition] = field(default_factory=list)
    status: AlertStatus = AlertStatus.ACTIVE
    push_enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_triggered_at: datetime | None = None
    trigger_count: int = 0
