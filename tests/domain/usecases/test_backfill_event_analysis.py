from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest

from scalper_today.domain.entities import AIAnalysis, EconomicEvent, Importance
from scalper_today.domain.usecases.events.backfill_event_analysis import (
    BackfillEventAnalysisUseCase,
)
from scalper_today.domain.usecases.events.cache_key_generator import CacheKeyGenerator


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_events_in_range.return_value = []
    return repo


@pytest.fixture
def mock_analyzer():
    analyzer = AsyncMock()
    analyzer.analyze_events.return_value = {}
    analyzer.analyze_events_deep.return_value = {}
    return analyzer


async def test_backfill_quick_analysis_without_provider(mock_repo, mock_analyzer):
    event = EconomicEvent(
        id="missing-ai",
        time="10:00",
        title="CPI",
        country="US",
        currency="USD",
        importance=Importance.MEDIUM,
        _timestamp=datetime(2026, 4, 29, 10, 0),
    )
    analysis = AIAnalysis(summary="Inflation context", impact="MEDIUM")
    mock_repo.get_events_in_range.return_value = [event]
    mock_analyzer.analyze_events.return_value = {CacheKeyGenerator.for_event(event): analysis}

    use_case = BackfillEventAnalysisUseCase(
        repository=mock_repo,
        analyzer=mock_analyzer,
        start_date=date(2026, 4, 29),
        end_date=date(2026, 4, 29),
    )

    result = await use_case.execute()

    assert result.total_events == 1
    assert result.quick_requested == 1
    assert result.quick_saved == 1
    assert result.deep_requested == 0
    assert result.deep_saved == 0
    mock_analyzer.analyze_events.assert_awaited_once_with([event])
    mock_analyzer.analyze_events_deep.assert_not_awaited()
    mock_repo.save_events_batch.assert_awaited_once_with([event], date(2026, 4, 29))


async def test_backfill_deep_analysis_when_requested(mock_repo, mock_analyzer):
    event = EconomicEvent(
        id="high-impact",
        time="10:00",
        title="NFP",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
        ai_analysis=AIAnalysis(summary="Quick context", impact="HIGH"),
        _timestamp=datetime(2026, 4, 29, 10, 0),
    )
    deep_analysis = AIAnalysis(
        summary="Deep context",
        impact="HIGH",
        macro_context="Labor market",
        is_deep_analysis=True,
    )
    mock_repo.get_events_in_range.return_value = [event]
    mock_analyzer.analyze_events_deep.return_value = {
        CacheKeyGenerator.for_event(event): deep_analysis
    }

    use_case = BackfillEventAnalysisUseCase(
        repository=mock_repo,
        analyzer=mock_analyzer,
        start_date=date(2026, 4, 29),
        end_date=date(2026, 4, 29),
    )

    result = await use_case.execute(include_deep=True)

    assert result.quick_requested == 0
    assert result.quick_saved == 0
    assert result.deep_requested == 1
    assert result.deep_saved == 1
    assert event.ai_analysis == deep_analysis
    mock_analyzer.analyze_events.assert_not_awaited()
    mock_analyzer.analyze_events_deep.assert_awaited_once_with([event])
    mock_repo.save_events_batch.assert_awaited_once_with([event], date(2026, 4, 29))


async def test_backfill_groups_saved_events_by_date(mock_repo, mock_analyzer):
    first_event = EconomicEvent(
        id="first",
        time="10:00",
        title="CPI",
        country="US",
        currency="USD",
        importance=Importance.MEDIUM,
        _timestamp=datetime(2026, 4, 29, 10, 0),
    )
    second_event = EconomicEvent(
        id="second",
        time="11:00",
        title="GDP",
        country="EU",
        currency="EUR",
        importance=Importance.MEDIUM,
        _timestamp=datetime(2026, 4, 30, 11, 0),
    )
    mock_repo.get_events_in_range.return_value = [first_event, second_event]
    mock_analyzer.analyze_events.return_value = {
        CacheKeyGenerator.for_event(first_event): AIAnalysis(summary="First"),
        CacheKeyGenerator.for_event(second_event): AIAnalysis(summary="Second"),
    }

    use_case = BackfillEventAnalysisUseCase(
        repository=mock_repo,
        analyzer=mock_analyzer,
        start_date=date(2026, 4, 29),
        end_date=date(2026, 4, 30),
    )

    await use_case.execute()

    mock_repo.save_events_batch.assert_any_await([first_event], date(2026, 4, 29))
    mock_repo.save_events_batch.assert_any_await([second_event], date(2026, 4, 30))
