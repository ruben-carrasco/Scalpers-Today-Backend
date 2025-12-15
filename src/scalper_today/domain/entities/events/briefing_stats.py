from dataclasses import dataclass


@dataclass
class BriefingStats:
    sentiment: str = "NEUTRAL"
    volatility_level: str = "LOW"
    total_events_today: int = 0
    high_impact_count: int = 0
