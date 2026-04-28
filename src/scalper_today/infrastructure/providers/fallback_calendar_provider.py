import logging
from datetime import date, timedelta

from scalper_today.domain.entities import EconomicEvent
from scalper_today.domain.interfaces import IEventProvider

logger = logging.getLogger(__name__)


class FallbackCalendarProvider(IEventProvider):
    def __init__(self, primary: IEventProvider, fallback: IEventProvider):
        self._primary = primary
        self._fallback = fallback

    async def fetch_today_events(self) -> list[EconomicEvent]:
        return await self.fetch_events_in_range(date.today(), date.today())

    async def fetch_events_in_range(self, start_date: date, end_date: date) -> list[EconomicEvent]:
        try:
            primary_events = await self._primary.fetch_events_in_range(start_date, end_date)
            if primary_events:
                return await self._merge_missing_dates(primary_events, start_date, end_date)
            logger.warning("Primary calendar provider returned no events; using fallback")
        except Exception as exc:
            logger.warning(
                "Primary calendar provider failed; using fallback", extra={"error": str(exc)}
            )

        return await self._fallback.fetch_events_in_range(start_date, end_date)

    async def _merge_missing_dates(
        self, primary_events: list[EconomicEvent], start_date: date, end_date: date
    ) -> list[EconomicEvent]:
        missing_dates = self._missing_dates(primary_events, start_date, end_date)
        if not missing_dates:
            return primary_events

        logger.warning(
            "Primary calendar provider returned partial range; filling missing dates",
            extra={"missing_dates": [day.isoformat() for day in sorted(missing_dates)]},
        )
        fallback_events = await self._fallback.fetch_events_in_range(start_date, end_date)
        if not fallback_events:
            return primary_events

        events_by_id = {event.id: event for event in primary_events}
        for event in fallback_events:
            if event._timestamp is None:
                continue
            if event._timestamp.date() in missing_dates:
                events_by_id[event.id] = event

        events = list(events_by_id.values())
        events.sort(
            key=lambda event: (
                event._timestamp.isoformat() if event._timestamp else "",
                event.time or "99:99",
                event.country or "ZZZ",
                -int(event.importance.value),
            )
        )
        return events

    @staticmethod
    def _missing_dates(events: list[EconomicEvent], start_date: date, end_date: date) -> set[date]:
        expected_dates = {
            start_date + timedelta(days=offset)
            for offset in range((end_date - start_date).days + 1)
        }
        covered_dates = {
            event._timestamp.date()
            for event in events
            if event._timestamp is not None and start_date <= event._timestamp.date() <= end_date
        }
        return expected_dates - covered_dates
