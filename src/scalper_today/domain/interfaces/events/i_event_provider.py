from abc import ABC, abstractmethod
from datetime import date

from scalper_today.domain.entities import EconomicEvent


class IEventProvider(ABC):
    @abstractmethod
    async def fetch_today_events(self) -> list[EconomicEvent]:
        pass

    @abstractmethod
    async def fetch_events_in_range(self, start_date: date, end_date: date) -> list[EconomicEvent]:
        pass
