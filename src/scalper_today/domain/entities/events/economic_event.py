from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .importance import Importance
from .ai_analysis import AIAnalysis


@dataclass
class EconomicEvent:
    id: str
    time: str
    title: str
    country: str
    currency: str
    importance: Importance
    actual: str = ""
    forecast: str = ""
    previous: str = ""
    surprise: str = "neutral"
    url: str = ""
    ai_analysis: Optional[AIAnalysis] = None
    _timestamp: Optional[datetime] = field(default=None, repr=False)

    @property
    def is_high_impact(self) -> bool:
        return self.importance == Importance.HIGH

    @property
    def has_data(self) -> bool:
        has_actual = bool(self.actual and self.actual.strip())
        return has_actual

    @property
    def cache_signature(self) -> str:
        signature = f"{self.time}|{self.country}|{self.title}|{self.actual}"
        return signature
