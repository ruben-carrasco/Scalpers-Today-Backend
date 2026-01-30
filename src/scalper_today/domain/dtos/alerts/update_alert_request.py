from dataclasses import dataclass
from typing import List, Optional


@dataclass
class UpdateAlertRequest:
    alert_id: str
    user_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[dict]] = None
    status: Optional[str] = None
    push_enabled: Optional[bool] = None
