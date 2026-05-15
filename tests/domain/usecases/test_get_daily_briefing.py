from datetime import date
from unittest.mock import AsyncMock

import pytest

from scalper_today.domain.entities import DailyBriefing, EconomicEvent, Importance
from scalper_today.domain.usecases import GetDailyBriefingUseCase


@pytest.fixture
def target_date() -> date:
    return date(2026, 5, 15)


@pytest.fixture
def sample_events() -> list[EconomicEvent]:
    return [
        EconomicEvent(
            id="event-1",
            time="10:00",
            title="Core CPI (MoM)",
            country="US",
            currency="USD",
            importance=Importance.HIGH,
        )
    ]


@pytest.fixture
def mock_repository(sample_events: list[EconomicEvent]) -> AsyncMock:
    repository = AsyncMock()
    repository.get_daily_briefing.return_value = None
    repository.is_cache_valid.return_value = True
    repository.get_events_by_date.return_value = sample_events
    return repository


@pytest.fixture
def mock_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.fetch_today_events.return_value = []
    return provider


@pytest.fixture
def mock_analyzer() -> AsyncMock:
    analyzer = AsyncMock()
    analyzer.generate_briefing.return_value = DailyBriefing(
        general_outlook="Sesión estable con volatilidad moderada.",
        impacted_assets=["EUR/USD"],
        cautionary_hours=["10:00"],
    )
    return analyzer


async def test_daily_briefing_uses_cached_when_valid_and_operational(
    target_date: date,
    mock_repository: AsyncMock,
    mock_provider: AsyncMock,
    mock_analyzer: AsyncMock,
):
    cached_briefing = DailyBriefing(
        general_outlook="Sesión mixta con foco en inflación.",
        impacted_assets=["EUR/USD"],
        cautionary_hours=["10:00"],
    )
    mock_repository.get_daily_briefing.return_value = cached_briefing
    mock_repository.is_cache_valid.return_value = True

    use_case = GetDailyBriefingUseCase(
        provider=mock_provider,
        repository=mock_repository,
        analyzer=mock_analyzer,
        target_date=target_date,
    )

    result = await use_case.execute()

    assert result == cached_briefing
    mock_analyzer.generate_briefing.assert_not_awaited()
    mock_repository.save_daily_briefing.assert_not_awaited()


async def test_daily_briefing_regenerates_when_cached_service_unavailable(
    target_date: date,
    sample_events: list[EconomicEvent],
    mock_repository: AsyncMock,
    mock_provider: AsyncMock,
    mock_analyzer: AsyncMock,
):
    cached_unavailable = DailyBriefing(
        general_outlook="Servicio de IA temporalmente no disponible",
        impacted_assets=[],
        cautionary_hours=[],
    )
    regenerated = DailyBriefing(
        general_outlook="Volatilidad media en la sesión europea.",
        impacted_assets=["DXY"],
        cautionary_hours=["14:30"],
    )

    mock_repository.get_daily_briefing.return_value = cached_unavailable
    mock_repository.is_cache_valid.return_value = True
    mock_analyzer.generate_briefing.return_value = regenerated

    use_case = GetDailyBriefingUseCase(
        provider=mock_provider,
        repository=mock_repository,
        analyzer=mock_analyzer,
        target_date=target_date,
    )

    result = await use_case.execute()

    assert result == regenerated
    mock_analyzer.generate_briefing.assert_awaited_once_with(sample_events)
    mock_repository.save_daily_briefing.assert_awaited_once_with(regenerated, target_date)


async def test_daily_briefing_does_not_cache_generated_unavailable_message(
    target_date: date,
    sample_events: list[EconomicEvent],
    mock_repository: AsyncMock,
    mock_provider: AsyncMock,
    mock_analyzer: AsyncMock,
):
    unavailable = DailyBriefing(
        general_outlook="Servicio de IA temporalmente no disponible",
        impacted_assets=[],
        cautionary_hours=[],
    )
    mock_repository.get_daily_briefing.return_value = None
    mock_analyzer.generate_briefing.return_value = unavailable

    use_case = GetDailyBriefingUseCase(
        provider=mock_provider,
        repository=mock_repository,
        analyzer=mock_analyzer,
        target_date=target_date,
    )

    result = await use_case.execute()

    assert result == unavailable
    mock_analyzer.generate_briefing.assert_awaited_once_with(sample_events)
    mock_repository.save_daily_briefing.assert_not_awaited()
