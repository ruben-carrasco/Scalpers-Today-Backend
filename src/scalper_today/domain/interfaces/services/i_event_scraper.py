from abc import ABC, abstractmethod
from typing import List

from scalper_today.domain.entities import EconomicEvent


class IEventScraper(ABC):
    @abstractmethod
    async def fetch_today_events(self) -> List[EconomicEvent]:
        pass
