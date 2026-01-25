from dataclasses import dataclass
from typing import Optional


@dataclass
class EventFilterCriteria:
    importance: Optional[int] = None
    country: Optional[str] = None
    has_data: Optional[bool] = None
    search: Optional[str] = None
