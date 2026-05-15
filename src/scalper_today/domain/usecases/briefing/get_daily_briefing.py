import logging
from datetime import date, datetime

import pytz

from scalper_today.domain.entities import DailyBriefing
from scalper_today.domain.interfaces import IAIAnalyzer, IEventProvider, IEventRepository

logger = logging.getLogger(__name__)

EMPTY_BRIEFING_MARKER = "relevancia significativa"
NON_CACHEABLE_BRIEFING_MARKERS = (
    "servicio de ia temporalmente no disponible",
    "error",
)


class GetDailyBriefingUseCase:
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

    async def execute(self) -> DailyBriefing:
        try:
            cached_briefing = await self._repository.get_daily_briefing(self._target_date)

            if cached_briefing:
                cache_valid = await self._repository.is_cache_valid(self._target_date)
                if cache_valid and self._is_cacheable_briefing(cached_briefing):
                    logger.info(f"Serving briefing for {self._target_date} from database cache")
                    return cached_briefing

                logger.info(
                    "Cached briefing ignored, regenerating",
                    extra={"cache_valid": cache_valid},
                )

            # Usamos los eventos ya almacenados en el repo antes de consultar el provider
            events = await self._repository.get_events_by_date(self._target_date)

            if not events:
                logger.info("No events in DB, fetching from provider for briefing")
                events = await self._provider.fetch_today_events()

            logger.info(f"Using {len(events)} events for briefing generation")

            logger.info("Generating new briefing with AI")
            briefing = await self._analyzer.generate_briefing(events)

            if self._is_cacheable_briefing(briefing):
                await self._repository.save_daily_briefing(briefing, self._target_date)
                logger.info(f"Briefing for {self._target_date} cached in database")
            else:
                logger.info("Generated briefing marked as non-cacheable, skipping persistence")

            return briefing

        except Exception as e:
            logger.error(f"Failed to generate briefing: {e}")
            return DailyBriefing.error(f"Error interno: {str(e)}")

    @staticmethod
    def _is_cacheable_briefing(briefing: DailyBriefing) -> bool:
        outlook = (briefing.general_outlook or "").strip().lower()
        if not outlook:
            return False

        if EMPTY_BRIEFING_MARKER in outlook:
            return False

        return not any(marker in outlook for marker in NON_CACHEABLE_BRIEFING_MARKERS)
