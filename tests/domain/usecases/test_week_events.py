from datetime import datetime, date
from unittest.mock import AsyncMock

import pytest

from scalper_today.domain.entities import EconomicEvent, Importance
from scalper_today.domain.usecases.events.get_week_events import GetWeekEventsUseCase


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.is_range_cache_valid.return_value = False
    repo.get_events_in_range.return_value = []
    return repo


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.fetch_events_in_range.return_value = []
    return provider


async def test_week_events_cache_hit(mock_repo, mock_provider):
    cached_event = EconomicEvent(
        id="1",
        time="10:00",
        title="Cached",
        country="US",
        currency="USD",
        importance=Importance.LOW,
        _timestamp=datetime(2026, 4, 13, 10, 0),
    )
    mock_repo.is_range_cache_valid.return_value = True
    mock_repo.get_events_in_range.return_value = [cached_event]

    use_case = GetWeekEventsUseCase(
        mock_provider,
        mock_repo,
        start_date=date(2026, 4, 13),
        end_date=date(2026, 4, 19),
    )

    events = await use_case.execute()

    assert events == [cached_event]
    mock_provider.fetch_events_in_range.assert_not_called()


async def test_week_events_refreshes_and_groups_by_date(mock_repo, mock_provider):
    monday_event = EconomicEvent(
        id="1",
        time="10:00",
        title="Monday",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
        _timestamp=datetime(2026, 4, 13, 10, 0),
    )
    wednesday_event = EconomicEvent(
        id="2",
        time="14:00",
        title="Wednesday",
        country="EU",
        currency="EUR",
        importance=Importance.MEDIUM,
        _timestamp=datetime(2026, 4, 15, 14, 0),
    )
    mock_provider.fetch_events_in_range.return_value = [monday_event, wednesday_event]
    mock_repo.get_events_in_range.side_effect = [[], [monday_event, wednesday_event]]

    use_case = GetWeekEventsUseCase(
        mock_provider,
        mock_repo,
        start_date=date(2026, 4, 13),
        end_date=date(2026, 4, 19),
    )

    events = await use_case.execute(force_refresh=True)

    assert events == [monday_event, wednesday_event]
    assert mock_repo.save_events_batch.await_count == 2
    mock_repo.save_events_batch.assert_any_await([monday_event], date(2026, 4, 13))
    mock_repo.save_events_batch.assert_any_await([wednesday_event], date(2026, 4, 15))
