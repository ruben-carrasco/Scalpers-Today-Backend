from datetime import datetime
from typing import List, Optional

import pytz

from scalper_today.domain.entities import EconomicEvent, DailyBriefing, HomeSummary
from scalper_today.domain.usecases.events.event_ordering import sort_events

TZ_MADRID = pytz.timezone("Europe/Madrid")


class GetHomeSummaryUseCase:
    MORNING_END_HOUR = 12
    AFTERNOON_END_HOUR = 20
    MAX_HIGHLIGHTS = 3
    HIGHLIGHT_TITLE_MAX_LENGTH = 40

    @staticmethod
    def get_greeting(hour: int) -> str:
        if hour < GetHomeSummaryUseCase.MORNING_END_HOUR:
            return "Buenos días"
        elif hour < GetHomeSummaryUseCase.AFTERNOON_END_HOUR:
            return "Buenas tardes"
        else:
            return "Buenas noches"

    @staticmethod
    def count_by_importance(events: List[EconomicEvent]) -> tuple:
        high = medium = low = 0
        for event in events:
            importance = int(event.importance)
            if importance == 3:
                high += 1
            elif importance == 2:
                medium += 1
            elif importance == 1:
                low += 1
        return high, medium, low

    @staticmethod
    def find_next_upcoming(
        events: List[EconomicEvent], current_time_str: str
    ) -> Optional[EconomicEvent]:
        return next((e for e in events if e.time >= current_time_str), None)

    @staticmethod
    def generate_highlights(
        events: List[EconomicEvent],
        current_time_str: Optional[str] = None,
    ) -> List[EconomicEvent]:
        if current_time_str:
            events = [e for e in events if e.time >= current_time_str]

        # Prioritize high impact (3 stars)
        highlights = [e for e in events if int(e.importance) == 3]

        # Fallback to medium impact (2 stars) if no high impact events exist
        if not highlights:
            highlights = [e for e in events if int(e.importance) == 2]

        return highlights[: GetHomeSummaryUseCase.MAX_HIGHLIGHTS]

    def execute(
        self,
        events: List[EconomicEvent],
        briefing: DailyBriefing,
        now: Optional[datetime] = None,
    ) -> HomeSummary:
        current_time = now or datetime.now(TZ_MADRID)
        current_time_str = current_time.strftime("%H:%M")
        ordered_events = sort_events(events)

        high, medium, low = self.count_by_importance(ordered_events)

        return HomeSummary(
            greeting=self.get_greeting(current_time.hour),
            date_formatted=current_time.strftime("%A, %d de %B %Y"),
            time_formatted=current_time.strftime("%H:%M"),
            total_events=len(ordered_events),
            high_impact_count=high,
            medium_impact_count=medium,
            low_impact_count=low,
            next_event=self.find_next_upcoming(ordered_events, current_time_str),
            sentiment=briefing.statistics.sentiment,
            volatility_level=briefing.statistics.volatility_level,
            highlights=self.generate_highlights(ordered_events, current_time_str),
        )
