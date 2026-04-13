from abc import ABC, abstractmethod
from typing import Dict, List

from scalper_today.domain.entities import AIAnalysis, DailyBriefing, EconomicEvent


class IAIAnalyzer(ABC):
    @abstractmethod
    async def analyze_events(self, events: List[EconomicEvent]) -> Dict[str, AIAnalysis]:
        pass

    @abstractmethod
    async def analyze_events_deep(self, events: List[EconomicEvent]) -> Dict[str, AIAnalysis]:
        pass

    @abstractmethod
    async def generate_briefing(self, events: List[EconomicEvent]) -> DailyBriefing:
        pass
