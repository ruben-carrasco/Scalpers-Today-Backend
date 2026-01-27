from dataclasses import dataclass
from typing import List
from scalper_today.domain.entities import EconomicEvent


@dataclass
class UpcomingEventsResult:
    current_time: str
    count: int
    events: List[EconomicEvent]
