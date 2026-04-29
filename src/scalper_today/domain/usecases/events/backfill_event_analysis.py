import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from scalper_today.domain.entities import AIAnalysis, EconomicEvent
from scalper_today.domain.interfaces import IAIAnalyzer, IEventRepository

from .cache_key_generator import CacheKeyGenerator
from .event_ordering import sort_events

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackfillEventAnalysisResult:
    total_events: int
    quick_requested: int
    quick_saved: int
    deep_requested: int
    deep_saved: int


class BackfillEventAnalysisUseCase:
    def __init__(
        self,
        repository: IEventRepository,
        analyzer: IAIAnalyzer,
        start_date: date,
        end_date: date,
    ):
        self._repository = repository
        self._analyzer = analyzer
        self._start_date = start_date
        self._end_date = end_date

    async def execute(self, include_deep: bool = False) -> BackfillEventAnalysisResult:
        events = sort_events(
            await self._repository.get_events_in_range(self._start_date, self._end_date)
        )
        logger.info(
            "Backfilling event analysis",
            extra={
                "start_date": str(self._start_date),
                "end_date": str(self._end_date),
                "total_events": len(events),
                "include_deep": include_deep,
            },
        )

        quick_missing = [event for event in events if event.ai_analysis is None]
        quick_saved_events = await self._backfill_quick(quick_missing)

        deep_missing: list[EconomicEvent] = []
        deep_saved_events: list[EconomicEvent] = []
        if include_deep:
            deep_missing = [
                event
                for event in events
                if event.is_high_impact
                and not (event.ai_analysis and event.ai_analysis.is_deep_analysis)
            ]
            deep_saved_events = await self._backfill_deep(deep_missing)

        return BackfillEventAnalysisResult(
            total_events=len(events),
            quick_requested=len(quick_missing),
            quick_saved=len(quick_saved_events),
            deep_requested=len(deep_missing),
            deep_saved=len(deep_saved_events),
        )

    async def _backfill_quick(self, events: list[EconomicEvent]) -> list[EconomicEvent]:
        if not events:
            return []

        results = await self._analyzer.analyze_events(events)
        saved_events = self._apply_analysis_results(events, results)
        await self._save_events_by_date(saved_events)
        return saved_events

    async def _backfill_deep(self, events: list[EconomicEvent]) -> list[EconomicEvent]:
        if not events:
            return []

        results = await self._analyzer.analyze_events_deep(events)
        saved_events = self._apply_analysis_results(events, results)
        await self._save_events_by_date(saved_events)
        return saved_events

    @staticmethod
    def _apply_analysis_results(
        events: list[EconomicEvent], results: dict[str, AIAnalysis]
    ) -> list[EconomicEvent]:
        saved_events = []
        for event in events:
            key = CacheKeyGenerator.for_event(event)
            if key not in results:
                continue
            event.ai_analysis = results[key]
            saved_events.append(event)
        return saved_events

    async def _save_events_by_date(self, events: list[EconomicEvent]) -> None:
        events_by_date: dict[date, list[EconomicEvent]] = defaultdict(list)
        for event in events:
            target_date = event._timestamp.date() if event._timestamp else self._start_date
            events_by_date[target_date].append(event)

        for target_date, day_events in events_by_date.items():
            await self._repository.save_events_batch(day_events, target_date)
