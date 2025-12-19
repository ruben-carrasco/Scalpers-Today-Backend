from dataclasses import dataclass
from typing import Optional

from .alert_type import AlertType


@dataclass
class AlertCondition:
    alert_type: AlertType
    value: Optional[str] = None
