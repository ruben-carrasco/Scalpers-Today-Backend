import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date
from scalper_today.infrastructure.providers.rapidapi_calendar_provider import (
    RapidApiCalendarProvider,
)
from scalper_today.infrastructure.providers.forexfactory_calendar_provider import (
    ForexFactoryCalendarProvider,
)
from scalper_today.infrastructure.providers.fallback_calendar_provider import (
    FallbackCalendarProvider,
)
from scalper_today.config import Settings


@pytest.fixture
def settings():
    return Settings(
        rapidapi_calendar_url="http://api.test",
        rapidapi_calendar_key="test-key",
        forexfactory_calendar_url="http://fallback.test",
    )


@pytest.fixture
def mock_http_client():
    return AsyncMock()


@pytest.mark.asyncio
async def test_fallback_when_primary_fails(settings, mock_http_client):
    # Setup primary (RapidAPI) to fail with 429
    mock_http_client.get.side_effect = [
        MagicMock(status_code=429),  # RapidAPI call
        MagicMock(
            status_code=200,
            json=lambda: [
                {"title": "Fallback Event", "date": "2026-04-29T10:00:00Z", "impact": "High"}
            ],
        ),  # Fallback call
    ]

    primary = RapidApiCalendarProvider(settings, mock_http_client)
    fallback = ForexFactoryCalendarProvider(settings, mock_http_client)
    composite = FallbackCalendarProvider(primary, fallback)

    events = await composite.fetch_events_in_range(date(2026, 4, 29), date(2026, 4, 29))

    assert len(events) == 1
    assert events[0].title == "Fallback Event"
    assert mock_http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fallback_when_primary_returns_empty(settings, mock_http_client):
    # Setup primary to return empty list
    mock_http_client.get.side_effect = [
        MagicMock(status_code=200, json=lambda: []),  # RapidAPI call
        MagicMock(
            status_code=200,
            json=lambda: [
                {"title": "Fallback Event", "date": "2026-04-29T10:00:00Z", "impact": "High"}
            ],
        ),  # Fallback call
    ]

    primary = RapidApiCalendarProvider(settings, mock_http_client)
    fallback = ForexFactoryCalendarProvider(settings, mock_http_client)
    composite = FallbackCalendarProvider(primary, fallback)

    events = await composite.fetch_events_in_range(date(2026, 4, 29), date(2026, 4, 29))

    assert len(events) == 1
    assert events[0].title == "Fallback Event"


@pytest.mark.asyncio
async def test_rapidapi_parsing_full_payload(settings, mock_http_client):
    payload = [
        {
            "title": "US CPI",
            "dateUtc": "2026-04-29T12:30:00Z",
            "currencyCode": "USD",
            "volatility": "High",
            "actual": "3.1%",
            "forecast": "3.0%",
            "previous": "2.9%",
        }
    ]
    mock_http_client.get.return_value = MagicMock(status_code=200, json=lambda: payload)

    provider = RapidApiCalendarProvider(settings, mock_http_client)
    events = await provider.fetch_events_in_range(date(2026, 4, 29), date(2026, 4, 29))

    assert len(events) == 1
    assert events[0].title == "US CPI"
    assert events[0].actual == "3.1%"
    assert events[0].surprise == "positive"  # 3.1 > 3.0


@pytest.mark.asyncio
async def test_forexfactory_parsing(settings, mock_http_client):
    payload = [
        {
            "title": "Unemployment Rate",
            "country": "AUD",
            "date": "2026-04-29T01:30:00Z",
            "impact": "High",
            "actual": "3.7%",
            "forecast": "3.8%",
            "previous": "3.9%",
        }
    ]
    mock_http_client.get.return_value = MagicMock(status_code=200, json=lambda: payload)

    provider = ForexFactoryCalendarProvider(settings, mock_http_client)
    events = await provider.fetch_events_in_range(date(2026, 4, 29), date(2026, 4, 29))

    assert len(events) == 1
    assert events[0].title == "Unemployment Rate"
    assert events[0].surprise == "negative"  # 3.7 < 3.8 (actual < forecast)
