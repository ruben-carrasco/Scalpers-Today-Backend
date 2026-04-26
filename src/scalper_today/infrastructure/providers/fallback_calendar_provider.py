import logging
from datetime import date

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
                return primary_events
            logger.warning("Primary calendar provider returned no events; using fallback")
        except Exception as exc:
            logger.warning(
                "Primary calendar provider failed; using fallback", extra={"error": str(exc)}
            )

        return await self._fallback.fetch_events_in_range(start_date, end_date)
