from abc import ABC, abstractmethod
from datetime import date, datetime

from scalper_today.domain.entities import DailyBriefing, EconomicEvent


class IEventRepository(ABC):
    @abstractmethod
    async def is_cache_valid(self, target_date: date) -> bool:
        pass

    @abstractmethod
    async def is_range_cache_valid(self, start_date: date, end_date: date) -> bool:
        pass

    @abstractmethod
    async def get_cache_last_update(self, target_date: date) -> datetime | None:
        pass

    @abstractmethod
    async def get_range_cache_last_update(
        self, start_date: date, end_date: date
    ) -> datetime | None:
        pass

    @abstractmethod
    async def get_events_by_date(
        self, target_date: date, only_missing_analysis: bool = False
    ) -> list[EconomicEvent]:
        pass

    @abstractmethod
    async def get_events_in_range(self, start_date: date, end_date: date) -> list[EconomicEvent]:
        pass

    @abstractmethod
    async def save_events_batch(self, events: list[EconomicEvent], target_date: date) -> None:
        pass

    @abstractmethod
    async def get_daily_briefing(self, target_date: date) -> DailyBriefing | None:
        pass

    @abstractmethod
    async def save_daily_briefing(self, briefing: DailyBriefing, target_date: date) -> None:
        pass
