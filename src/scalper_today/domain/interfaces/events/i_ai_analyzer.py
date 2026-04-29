from abc import ABC, abstractmethod

from scalper_today.domain.entities import AIAnalysis, DailyBriefing, EconomicEvent


class IAIAnalyzer(ABC):
    @abstractmethod
    async def analyze_events(self, events: list[EconomicEvent]) -> dict[str, AIAnalysis]:
        pass

    @abstractmethod
    async def analyze_events_deep(self, events: list[EconomicEvent]) -> dict[str, AIAnalysis]:
        pass

    @abstractmethod
    async def generate_briefing(self, events: list[EconomicEvent]) -> DailyBriefing:
        pass
