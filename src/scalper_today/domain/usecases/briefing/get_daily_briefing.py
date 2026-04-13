import logging
from datetime import date, datetime

import pytz

from scalper_today.domain.entities import DailyBriefing
from scalper_today.domain.interfaces import IAIAnalyzer, IEventProvider, IEventRepository

logger = logging.getLogger(__name__)


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
                # Si el briefing guardado es el mensaje de "no hay eventos", intentamos regenerar
                # por si ahora hay eventos de impacto medio disponibles para el fallback
                is_empty_briefing = "relevancia significativa" in cached_briefing.general_outlook

                cache_valid = await self._repository.is_cache_valid(self._target_date)
                if cache_valid and not is_empty_briefing:
                    logger.info(f"Serving briefing for {self._target_date} from database cache")
                    return cached_briefing

                logger.info("Briefing cache expired or empty, regenerating...")

            # Usamos los eventos ya almacenados en el repo antes de consultar el provider
            events = await self._repository.get_events_by_date(self._target_date)

            if not events:
                logger.info("No events in DB, fetching from provider for briefing")
                events = await self._provider.fetch_today_events()

            logger.info(f"Using {len(events)} events for briefing generation")

            logger.info("Generating new briefing with AI")
            briefing = await self._analyzer.generate_briefing(events)

            # Solo guardamos si el análisis es real (no un error o un disclaimer de "no hay eventos")
            if "Error" not in briefing.general_outlook:
                await self._repository.save_daily_briefing(briefing, self._target_date)
                logger.info(f"Briefing for {self._target_date} cached in database")

            return briefing

        except Exception as e:
            logger.error(f"Failed to generate briefing: {e}")
            return DailyBriefing.error(f"Error interno: {str(e)}")
