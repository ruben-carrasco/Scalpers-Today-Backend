import logging
from collections import defaultdict
from datetime import date
from typing import List

from scalper_today.domain.entities import EconomicEvent
from scalper_today.domain.interfaces import IEventProvider, IEventRepository
from .event_ordering import sort_events

logger = logging.getLogger(__name__)


class GetWeekEventsUseCase:
    def __init__(
        self,
        provider: IEventProvider,
        repository: IEventRepository,
        start_date: date,
        end_date: date,
    ):
        self._provider = provider
        self._repository = repository
        self._start_date = start_date
        self._end_date = end_date

    async def execute(self, force_refresh: bool = False) -> List[EconomicEvent]:
        logger.info(
            "Fetching week events",
            extra={"start_date": str(self._start_date), "end_date": str(self._end_date)},
        )

        cached_events = await self._repository.get_events_in_range(self._start_date, self._end_date)
        if not force_refresh and cached_events:
            range_cache_valid = await self._repository.is_range_cache_valid(
                self._start_date, self._end_date
            )
            if range_cache_valid:
                logger.info("Returning cached week events", extra={"count": len(cached_events)})
                return sort_events(cached_events)

        provider_events = await self._provider.fetch_events_in_range(
            self._start_date, self._end_date
        )
        if not provider_events:
            logger.warning("Week provider returned no events")
            return cached_events

        events_by_day: dict[date, list[EconomicEvent]] = defaultdict(list)
        for event in provider_events:
            if event._timestamp is None:
                continue
            events_by_day[event._timestamp.date()].append(event)

        for target_date, day_events in events_by_day.items():
            await self._repository.save_events_batch(day_events, target_date)

        refreshed_events = await self._repository.get_events_in_range(
            self._start_date, self._end_date
        )
        logger.info("Returning refreshed week events", extra={"count": len(refreshed_events)})
        return sort_events(refreshed_events)
