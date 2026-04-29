from dataclasses import dataclass

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
    next_event: EconomicEvent | None
    sentiment: str
    volatility_level: str
    highlights: list[EconomicEvent]
