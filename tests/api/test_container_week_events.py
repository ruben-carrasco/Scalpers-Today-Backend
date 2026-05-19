import asyncio
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import scalper_today.api.dependencies.container as container_module
from scalper_today.api.dependencies.container import Container
from scalper_today.domain.entities import EconomicEvent, Importance
from scalper_today.domain.usecases.events.backfill_event_analysis import (
    BackfillEventAnalysisResult,
)


class FakeSessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeDatabaseManager:
    def session(self):
        return FakeSessionContext()


@pytest.fixture
def week_event() -> EconomicEvent:
    return EconomicEvent(
        id="week-event",
        time="10:00",
        title="CPI",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
        _timestamp=datetime(2026, 5, 19, 10, 0),
    )


def build_container(repository: AsyncMock, analyzer: AsyncMock) -> Container:
    container = Container(
        settings=SimpleNamespace(calendar_cache_ttl_minutes=10080),
        http_client=AsyncMock(),
        database_manager=FakeDatabaseManager(),
        provider=AsyncMock(),
        analyzer=analyzer,
        jwt_service=AsyncMock(),
        password_reset_notifier=AsyncMock(),
    )
    container.get_event_repository = lambda _session: repository
    return container


async def test_week_events_returns_events_when_ai_backfill_times_out(
    monkeypatch,
    week_event: EconomicEvent,
):
    repository = AsyncMock()
    repository.get_events_in_range.return_value = [week_event]
    repository.is_range_cache_valid.return_value = True

    analyzer = AsyncMock()

    async def slow_execute(include_deep: bool = False):
        await asyncio.sleep(1)

    monkeypatch.setattr(container_module, "WEEK_ANALYSIS_BACKFILL_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(
        container_module.BackfillEventAnalysisUseCase,
        "execute",
        slow_execute,
    )
    container = build_container(repository, analyzer)

    events = await container.get_week_events(
        start_date=date(2026, 5, 18),
        end_date=date(2026, 5, 24),
    )

    assert events == [week_event]


async def test_week_events_reloads_events_when_ai_backfill_saves_analysis(
    monkeypatch,
    week_event: EconomicEvent,
):
    refreshed_event = EconomicEvent(
        id="week-event",
        time="10:00",
        title="CPI",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
        _timestamp=datetime(2026, 5, 19, 10, 0),
    )
    repository = AsyncMock()
    repository.get_events_in_range.side_effect = [[week_event], [week_event], [refreshed_event]]
    repository.is_range_cache_valid.return_value = True

    analyzer = AsyncMock()
    monkeypatch.setattr(
        container_module.BackfillEventAnalysisUseCase,
        "execute",
        AsyncMock(
            return_value=BackfillEventAnalysisResult(
                total_events=1,
                quick_requested=1,
                quick_saved=1,
                deep_requested=0,
                deep_saved=0,
            )
        ),
    )
    container = build_container(repository, analyzer)

    events = await container.get_week_events(
        start_date=date(2026, 5, 18),
        end_date=date(2026, 5, 24),
    )

    assert events == [refreshed_event]
