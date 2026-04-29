from dataclasses import dataclass

from .alert_type import AlertType


@dataclass
class AlertCondition:
    alert_type: AlertType
    value: str | None = None
