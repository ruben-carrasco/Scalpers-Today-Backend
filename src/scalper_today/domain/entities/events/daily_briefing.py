from dataclasses import dataclass, field
from typing import List

from .briefing_stats import BriefingStats


@dataclass
class DailyBriefing:
    general_outlook: str
    impacted_assets: List[str]
    cautionary_hours: List[str]
    statistics: BriefingStats = field(default_factory=BriefingStats)
    key_themes: List[str] = field(default_factory=list)

    @classmethod
    def empty_day(cls, total_events: int = 0) -> "DailyBriefing":
        return cls(
            general_outlook="Hoy no se han detectado eventos económicos de relevancia significativa.",
            impacted_assets=[],
            cautionary_hours=[],
            statistics=BriefingStats(total_events_today=total_events),
        )

    @classmethod
    def error(cls, message: str = "Error generando análisis") -> "DailyBriefing":
        briefing = cls(general_outlook=message, impacted_assets=[], cautionary_hours=[])
        return briefing
