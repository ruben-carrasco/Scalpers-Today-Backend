import logging
from datetime import date, datetime
from typing import List

import pytz

from scalper_today.domain.entities import EconomicEvent
from scalper_today.domain.interfaces import IAIAnalyzer, IEventProvider, IEventRepository
from .cache_key_generator import CacheKeyGenerator

logger = logging.getLogger(__name__)


class GetMacroEventsUseCase:
    def __init__(
        self,
        provider: IEventProvider,
        repository: IEventRepository,
        analyzer: IAIAnalyzer,
        target_date: date | None = None,
    ):
        self._provider = provider
        self._repository = repository
        self._analyzer = analyzer
        self._target_date = target_date or datetime.now(pytz.timezone("Europe/Madrid")).date()

    async def execute(self, force_refresh: bool = False) -> List[EconomicEvent]:
        logger.info(f"Fetching events for {self._target_date}")

        if not force_refresh:
            cache_valid = await self._repository.is_cache_valid(self._target_date)
            if cache_valid:
                cached_events = await self._repository.get_events_by_date(self._target_date)
                if cached_events:
                    logger.info(f"Cache valid, returning {len(cached_events)} events from database")
                    return cached_events

            cached_events = await self._repository.get_events_by_date(self._target_date)
            if cached_events:
                logger.info("Cache expired, re-fetching provider data to check for updates...")
            else:
                logger.info("No events in database for today")

        logger.info("Fetching fresh events from provider...")
        scraped_events = await self._provider.fetch_today_events()

        if not scraped_events:
            logger.warning("No events fetched from provider")
            return await self._repository.get_events_by_date(self._target_date)

        logger.info(f"Scraped {len(scraped_events)} events")

        await self._repository.save_events_batch(scraped_events, self._target_date)
        logger.info("Events saved to database")

        all_events = await self._repository.get_events_by_date(self._target_date)
        logger.info(f"Loaded {len(all_events)} events from database")

        events_needing_quick = [e for e in all_events if e.ai_analysis is None]

        if events_needing_quick:
            logger.info(f"Performing quick analysis on {len(events_needing_quick)} events")
            quick_results = await self._analyzer.analyze_events(events_needing_quick)

            for event in events_needing_quick:
                key = CacheKeyGenerator.for_event(event)
                if key in quick_results:
                    event.ai_analysis = quick_results[key]

            await self._repository.save_events_batch(events_needing_quick, self._target_date)
            logger.info(f"Quick analysis saved for {len(quick_results)} events")
        else:
            logger.info("All events already have quick analysis")

        high_impact_events = [e for e in all_events if e.is_high_impact]
        high_impact_needing_deep = [
            e for e in high_impact_events if not (e.ai_analysis and e.ai_analysis.is_deep_analysis)
        ]

        if high_impact_needing_deep:
            logger.info(
                f"Performing deep analysis on {len(high_impact_needing_deep)} high-impact events"
            )
            deep_results = await self._analyzer.analyze_events_deep(high_impact_needing_deep)

            for event in high_impact_needing_deep:
                key = CacheKeyGenerator.for_event(event)
                if key in deep_results:
                    event.ai_analysis = deep_results[key]

            await self._repository.save_events_batch(high_impact_needing_deep, self._target_date)
            logger.info(f"Deep analysis saved for {len(deep_results)} high-impact events")
        else:
            logger.info(
                f"All {len(high_impact_events)} high-impact events already have deep analysis"
            )

        final_events = await self._repository.get_events_by_date(self._target_date)

        with_quick = sum(1 for e in final_events if e.ai_analysis is not None)
        with_deep = sum(1 for e in final_events if e.ai_analysis and e.ai_analysis.is_deep_analysis)

        logger.info(
            f"Returning {len(final_events)} events: "
            f"{with_quick} with quick analysis, {with_deep} with deep analysis"
        )

        return final_events
