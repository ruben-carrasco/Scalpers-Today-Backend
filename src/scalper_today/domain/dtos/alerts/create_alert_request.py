from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CreateAlertRequest:
    user_id: str
    name: str
    description: Optional[str] = None
    conditions: List[dict] = None
    push_enabled: bool = True
