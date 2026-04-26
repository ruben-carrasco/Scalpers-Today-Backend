import json
import logging
from datetime import datetime, date, timezone
from typing import List, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from scalper_today.domain import EconomicEvent, AIAnalysis, DailyBriefing, BriefingStats
from scalper_today.domain.interfaces import IEventRepository
from ..models import EventModel, DailyBriefingModel

logger = logging.getLogger(__name__)

CACHE_TTL_MINUTES = 5


class EventRepository(IEventRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_cache_last_update(self, target_date: date) -> Optional[datetime]:
        query = select(func.max(EventModel.updated_at)).where(
            *self._range_clause(target_date, target_date)
        )
        result = await self._session.execute(query)
        return result.scalar()

    async def get_range_cache_last_update(
        self, start_date: date, end_date: date
    ) -> Optional[datetime]:
        query = select(func.max(EventModel.updated_at)).where(
            *self._range_clause(start_date, end_date)
        )
        result = await self._session.execute(query)
        return result.scalar()

    async def is_cache_valid(self, target_date: date) -> bool:
        last_update = await self.get_cache_last_update(target_date)
        return self._is_cache_timestamp_valid(last_update)

    async def is_range_cache_valid(self, start_date: date, end_date: date) -> bool:
        last_update = await self.get_range_cache_last_update(start_date, end_date)
        return self._is_cache_timestamp_valid(last_update)

    @staticmethod
    def _is_cache_timestamp_valid(last_update: Optional[datetime]) -> bool:
        if last_update is None:
            return False
        now = datetime.now(timezone.utc)
        if last_update.tzinfo is None:
            now = now.replace(tzinfo=None)

        age_minutes = (now - last_update).total_seconds() / 60
        is_valid = age_minutes < CACHE_TTL_MINUTES

        logger.info(
            f"Cache age: {age_minutes:.1f} min, TTL: {CACHE_TTL_MINUTES} min, valid: {is_valid}"
        )
        return is_valid

    async def get_events_by_date(
        self, target_date: date, only_missing_analysis: bool = False
    ) -> List[EconomicEvent]:
        query = select(EventModel).where(*self._range_clause(target_date, target_date))

        if only_missing_analysis:
            query = query.where(EventModel.has_quick_analysis is False)

        query = query.order_by(EventModel.time, EventModel.country, EventModel.importance.desc())

        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_domain(model) for model in models]

    async def get_events_in_range(self, start_date: date, end_date: date) -> List[EconomicEvent]:
        query = (
            select(EventModel)
            .where(*self._range_clause(start_date, end_date))
            .order_by(
                EventModel.date, EventModel.time, EventModel.country, EventModel.importance.desc()
            )
        )

        result = await self._session.execute(query)
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def get_high_impact_events(
        self, target_date: date, only_missing_deep_analysis: bool = False
    ) -> List[EconomicEvent]:
        query = select(EventModel).where(
            and_(
                EventModel.date >= datetime.combine(target_date, datetime.min.time()),
                EventModel.date < datetime.combine(target_date, datetime.max.time()),
                EventModel.importance == 3,
            )
        )

        if only_missing_deep_analysis:
            query = query.where(EventModel.has_deep_analysis is False)

        query = query.order_by(EventModel.time, EventModel.country, EventModel.importance.desc())

        result = await self._session.execute(query)
        models = result.scalars().all()

        return [self._to_domain(model) for model in models]

    async def save_event(self, event: EconomicEvent, target_date: date) -> None:
        existing = await self._session.get(EventModel, event.id)

        if existing:
            self._update_from_domain(existing, event, target_date)
        else:
            model = self._to_model(event, target_date)
            self._session.add(model)

    async def save_events_batch(self, events: List[EconomicEvent], target_date: date) -> None:
        for event in events:
            await self.save_event(event, target_date)

        logger.info(f"Saved batch of {len(events)} events for {target_date}")

    async def get_daily_briefing(self, target_date: date) -> Optional[DailyBriefing]:
        briefing_date = datetime.combine(target_date, datetime.min.time())
        model = await self._session.get(DailyBriefingModel, briefing_date)

        if not model:
            return None

        return self._briefing_to_domain(model)

    async def save_daily_briefing(self, briefing: DailyBriefing, target_date: date) -> None:
        briefing_date = datetime.combine(target_date, datetime.min.time())
        existing = await self._session.get(DailyBriefingModel, briefing_date)

        if existing:
            self._update_briefing_from_domain(existing, briefing)
        else:
            model = self._briefing_to_model(briefing, briefing_date)
            self._session.add(model)

        logger.info(f"Saved daily briefing for {target_date}")

    # --- Domain <-> Model Conversion ---

    @staticmethod
    def _to_domain(model: EventModel) -> EconomicEvent:
        from scalper_today.domain.entities import Importance

        ai_analysis = None
        if model.has_quick_analysis:
            if model.has_deep_analysis:
                ai_analysis = AIAnalysis(
                    summary=model.deep_summary or model.quick_summary or "",
                    impact=model.quick_impact or "N/A",
                    sentiment=model.quick_sentiment or "NEUTRAL",
                )
                if model.macro_context:
                    ai_analysis.macro_context = model.macro_context
                if model.technical_levels:
                    ai_analysis.technical_levels = model.technical_levels
                if model.trading_strategies:
                    ai_analysis.trading_strategies = model.trading_strategies
                if model.impacted_assets:
                    try:
                        ai_analysis.impacted_assets = json.loads(model.impacted_assets)
                    except (json.JSONDecodeError, TypeError):
                        ai_analysis.impacted_assets = model.impacted_assets
            else:
                ai_analysis = AIAnalysis(
                    summary=model.quick_summary or "",
                    impact=model.quick_impact or "N/A",
                    sentiment=model.quick_sentiment or "NEUTRAL",
                )

        return EconomicEvent(
            id=model.id,
            time=model.time,
            title=model.title,
            country=model.country,
            currency=model.currency,
            importance=Importance(model.importance),
            actual=model.actual,
            forecast=model.forecast,
            previous=model.previous,
            surprise=model.surprise,
            url=model.url,
            ai_analysis=ai_analysis,
            _timestamp=model.date,
        )

    @staticmethod
    def _to_model(event: EconomicEvent, target_date: date) -> EventModel:
        model = EventModel(
            id=event.id,
            date=datetime.combine(target_date, datetime.min.time()),
            time=event.time,
            title=event.title,
            country=event.country,
            currency=event.currency,
            importance=int(event.importance),
            actual=event.actual,
            forecast=event.forecast,
            previous=event.previous,
            surprise=event.surprise,
            url=event.url,
        )

        EventRepository._update_analysis_fields(model, event)
        return model

    @staticmethod
    def _update_from_domain(model: EventModel, event: EconomicEvent, target_date: date) -> None:
        old_actual = (model.actual or "").strip()
        new_actual = (event.actual or "").strip()
        actual_data_arrived = (not old_actual) and bool(new_actual)

        model.date = datetime.combine(target_date, datetime.min.time())
        model.time = event.time
        model.title = event.title
        model.country = event.country
        model.currency = event.currency
        model.importance = int(event.importance)
        model.actual = event.actual
        model.forecast = event.forecast
        model.previous = event.previous
        model.surprise = event.surprise
        model.url = event.url

        if actual_data_arrived:
            logger.info(
                f"Event '{event.title}' got actual data '{new_actual}', invalidating AI analysis"
            )
            model.quick_summary = None
            model.quick_impact = None
            model.quick_sentiment = None
            model.deep_summary = None
            model.macro_context = None
            model.technical_levels = None
            model.trading_strategies = None
            model.impacted_assets = None
            model.has_quick_analysis = False
            model.has_deep_analysis = False
        else:
            EventRepository._update_analysis_fields(model, event)

    @staticmethod
    def _update_analysis_fields(model: EventModel, event: EconomicEvent) -> None:
        if event.ai_analysis:
            is_deep = event.ai_analysis.is_deep_analysis

            if is_deep:
                model.deep_summary = event.ai_analysis.summary
                model.quick_impact = event.ai_analysis.impact
                model.quick_sentiment = event.ai_analysis.sentiment
                model.macro_context = event.ai_analysis.macro_context
                model.technical_levels = event.ai_analysis.technical_levels
                model.trading_strategies = event.ai_analysis.trading_strategies

                assets = event.ai_analysis.impacted_assets
                if assets and isinstance(assets, list):
                    model.impacted_assets = json.dumps(assets)
                elif assets:
                    model.impacted_assets = assets
                else:
                    model.impacted_assets = None

                model.has_deep_analysis = True
                model.has_quick_analysis = True
            else:
                model.quick_summary = event.ai_analysis.summary
                model.quick_impact = event.ai_analysis.impact
                model.quick_sentiment = event.ai_analysis.sentiment
                model.has_quick_analysis = True

    @staticmethod
    def _briefing_to_domain(model: DailyBriefingModel) -> DailyBriefing:
        try:
            impacted_assets = json.loads(model.impacted_assets)
        except (json.JSONDecodeError, TypeError):
            impacted_assets = []
        try:
            cautionary_hours = json.loads(model.cautionary_hours)
        except (json.JSONDecodeError, TypeError):
            cautionary_hours = []

        return DailyBriefing(
            general_outlook=model.general_outlook,
            impacted_assets=impacted_assets,
            cautionary_hours=cautionary_hours,
            statistics=BriefingStats(
                sentiment=model.sentiment,
                volatility_level=model.volatility_level,
                total_events_today=model.total_events,
                high_impact_count=model.high_impact_count,
            ),
        )

    @staticmethod
    def _briefing_to_model(briefing: DailyBriefing, briefing_date: datetime) -> DailyBriefingModel:
        return DailyBriefingModel(
            date=briefing_date,
            general_outlook=briefing.general_outlook,
            impacted_assets=json.dumps(briefing.impacted_assets),
            cautionary_hours=json.dumps(briefing.cautionary_hours),
            sentiment=briefing.statistics.sentiment,
            volatility_level=briefing.statistics.volatility_level,
            total_events=briefing.statistics.total_events_today,
            high_impact_count=briefing.statistics.high_impact_count,
        )

    @staticmethod
    def _update_briefing_from_domain(model: DailyBriefingModel, briefing: DailyBriefing) -> None:
        model.general_outlook = briefing.general_outlook
        model.impacted_assets = json.dumps(briefing.impacted_assets)
        model.cautionary_hours = json.dumps(briefing.cautionary_hours)
        model.sentiment = briefing.statistics.sentiment
        model.volatility_level = briefing.statistics.volatility_level
        model.total_events = briefing.statistics.total_events_today
        model.high_impact_count = briefing.statistics.high_impact_count

    @staticmethod
    def _range_clause(start_date: date, end_date: date):
        range_start = datetime.combine(start_date, datetime.min.time())
        range_end = datetime.combine(end_date, datetime.max.time())
        return (
            EventModel.date >= range_start,
            EventModel.date <= range_end,
        )
