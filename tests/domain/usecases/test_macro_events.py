import pytest
from unittest.mock import AsyncMock

from scalper_today.domain.usecases import GetMacroEventsUseCase
from scalper_today.domain.entities import AIAnalysis, EconomicEvent
from scalper_today.domain.entities import Importance
from scalper_today.domain.usecases.events.cache_key_generator import CacheKeyGenerator


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.is_cache_valid.return_value = False
    repo.get_events_by_date.return_value = []
    return repo


@pytest.fixture
def mock_scraper():
    scraper = AsyncMock()
    scraper.fetch_today_events.return_value = []
    return scraper


@pytest.fixture
def mock_analyzer():
    analyzer = AsyncMock()
    analyzer.analyze_events.return_value = {}
    analyzer.analyze_events_deep.return_value = {}
    return analyzer


async def test_macro_events_cache_hit(mock_repo, mock_scraper, mock_analyzer):
    # Setup cache hit
    mock_repo.is_cache_valid.return_value = True
    cached_event = EconomicEvent(
        id="1",
        time="10:00",
        title="Cached",
        country="US",
        currency="USD",
        importance=Importance.LOW,
    )
    mock_repo.get_events_by_date.return_value = [cached_event]

    usecase = GetMacroEventsUseCase(mock_scraper, mock_repo, mock_analyzer)
    events = await usecase.execute(force_refresh=False)

    assert len(events) == 1
    assert events[0].title == "Cached"
    # Scraper should NOT be called
    mock_scraper.fetch_today_events.assert_not_called()


async def test_macro_events_cache_hit_completes_missing_ai_without_provider(
    mock_repo, mock_scraper, mock_analyzer
):
    mock_repo.is_cache_valid.return_value = True
    cached_event = EconomicEvent(
        id="1",
        time="10:00",
        title="Cached",
        country="US",
        currency="USD",
        importance=Importance.LOW,
    )
    analysis = AIAnalysis(summary="Cached event analysis", impact="Medium")
    mock_repo.get_events_by_date.return_value = [cached_event]
    mock_analyzer.analyze_events.return_value = {
        CacheKeyGenerator.for_event(cached_event): analysis
    }

    usecase = GetMacroEventsUseCase(mock_scraper, mock_repo, mock_analyzer)
    events = await usecase.execute(force_refresh=False)

    assert events[0].ai_analysis == analysis
    mock_scraper.fetch_today_events.assert_not_called()
    mock_analyzer.analyze_events.assert_awaited_once_with([cached_event])
    mock_analyzer.analyze_events_deep.assert_not_awaited()
    mock_repo.save_events_batch.assert_awaited()


async def test_macro_events_cache_hit_skips_deep_ai_completion(
    mock_repo, mock_scraper, mock_analyzer
):
    mock_repo.is_cache_valid.return_value = True
    cached_event = EconomicEvent(
        id="1",
        time="10:00",
        title="Cached high impact",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
        ai_analysis=AIAnalysis(summary="Quick analysis", impact="High"),
    )
    mock_repo.get_events_by_date.return_value = [cached_event]

    usecase = GetMacroEventsUseCase(mock_scraper, mock_repo, mock_analyzer)
    events = await usecase.execute(force_refresh=False)

    assert events == [cached_event]
    mock_scraper.fetch_today_events.assert_not_called()
    mock_analyzer.analyze_events.assert_not_awaited()
    mock_analyzer.analyze_events_deep.assert_not_awaited()


async def test_macro_events_cache_miss_and_scrape(mock_repo, mock_scraper, mock_analyzer):
    # Setup cache miss
    mock_repo.is_cache_valid.return_value = False
    scraped_event = EconomicEvent(
        id="2",
        time="11:00",
        title="Scraped",
        country="EU",
        currency="EUR",
        importance=Importance.HIGH,
    )
    mock_scraper.fetch_today_events.return_value = [scraped_event]

    # Repository must return the list after saving
    mock_repo.get_events_by_date.return_value = [scraped_event]

    usecase = GetMacroEventsUseCase(mock_scraper, mock_repo, mock_analyzer)
    events = await usecase.execute()

    assert len(events) == 1
    assert events[0].title == "Scraped"
    # Scraper SHOULD be called
    mock_scraper.fetch_today_events.assert_called_once()
    # Should save to repo
    mock_repo.save_events_batch.assert_called()
