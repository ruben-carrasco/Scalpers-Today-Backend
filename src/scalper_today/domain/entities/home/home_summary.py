from dataclasses import dataclass
from typing import List, Optional

from ..events.economic_event import EconomicEvent


@dataclass
class HomeSummary:
    greeting: str
    date_formatted: str
    time_formatted: str
    total_events: int
    high_impact_count: int
    medium_impact_count: int
    low_impact_count: int
    next_event: Optional[EconomicEvent]
    sentiment: str
    volatility_level: str
    highlights: List[EconomicEvent]
