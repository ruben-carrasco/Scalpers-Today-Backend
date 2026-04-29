from datetime import datetime

import pytz

from scalper_today.domain.dtos import UpcomingEventsResult
from scalper_today.domain.entities import EconomicEvent

TZ_MADRID = pytz.timezone("Europe/Madrid")


class GetUpcomingEventsUseCase:
    DEFAULT_LIMIT = 5

    def execute(
        self,
        events: list[EconomicEvent],
        limit: int = DEFAULT_LIMIT,
        now: datetime | None = None,
    ) -> UpcomingEventsResult:
        current_time = now or datetime.now(TZ_MADRID)
        current_time_str = current_time.strftime("%H:%M")

        upcoming = []
        for event in events:
            if event.time >= current_time_str:
                upcoming.append(event)
                if len(upcoming) >= limit:
                    break

        result = UpcomingEventsResult(
            current_time=current_time_str,
            count=len(upcoming),
            events=upcoming,
        )

        return result
