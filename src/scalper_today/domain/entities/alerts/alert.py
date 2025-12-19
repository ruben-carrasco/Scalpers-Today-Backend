from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List

from .alert_status import AlertStatus
from .alert_condition import AlertCondition


@dataclass
class Alert:
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    conditions: List[AlertCondition] = field(default_factory=list)
    status: AlertStatus = AlertStatus.ACTIVE
    push_enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
