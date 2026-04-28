from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from scalper_today.config import Settings
from scalper_today.domain.entities import EconomicEvent, Importance
from scalper_today.infrastructure.providers import (
    FallbackCalendarProvider,
    RapidApiCalendarProvider,
)


def make_response(status_code: int = 200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def make_settings(**overrides) -> Settings:
    defaults = {
        "rapidapi_calendar_key": "rapid-key",
        "rapidapi_calendar_host": "economic-calendar-api.p.rapidapi.com",
        "rapidapi_calendar_url": "https://economic-calendar-api.p.rapidapi.com/calendar",
        "rapidapi_calendar_timezone": "GMT+0",
        "rapidapi_calendar_limit": 500,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_parse_payload_maps_rapidapi_fields():
    provider = RapidApiCalendarProvider(make_settings(), MagicMock())
    payload = {
        "data": [
            {
                "id": "nfp-20260427",
                "eventId": "ace93e5e-f249-452c-8c63-883ff2ee8732",
                "name": "Non-Farm Payrolls",
                "countryCode": "US",
                "currencyCode": "USD",
                "dateUtc": "2026-04-27T12:30:00.000Z",
                "volatility": "HIGH",
                "actual": "225K",
                "consensus": "180K",
                "previous": "150K",
                "isBetterThanExpected": True,
            }
        ]
    }

    events = provider._parse_payload(payload, date(2026, 4, 27), date(2026, 4, 27))

    assert len(events) == 1
    event = events[0]
    assert event.id == "rapidapi-nfp-20260427"
    assert event.title == "Non-Farm Payrolls"
    assert event.country == "US"
    assert event.currency == "USD"
    assert event.importance == Importance.HIGH
    assert event.actual == "225K"
    assert event.forecast == "180K"
    assert event.previous == "150K"
    assert event.surprise == "positive"


@pytest.mark.asyncio
async def test_fetch_events_in_range_sends_rapidapi_headers_and_params():
    client = MagicMock()
    client.get = AsyncMock(return_value=make_response(json_data=[]))
    settings = make_settings()
    provider = RapidApiCalendarProvider(settings, client)

    events = await provider.fetch_events_in_range(date(2026, 4, 27), date(2026, 5, 3))

    assert events == []
    client.get.assert_awaited_once()
    _, kwargs = client.get.await_args
    assert kwargs["headers"]["X-RapidAPI-Key"] == "rapid-key"
    assert kwargs["headers"]["X-RapidAPI-Host"] == settings.rapidapi_calendar_host
    assert kwargs["params"]["startDate"] == "2026-04-27"
    assert kwargs["params"]["endDate"] == "2026-05-03"
    assert kwargs["params"]["timezone"] == "GMT+0"
    assert kwargs["params"]["limit"] == 500


@pytest.mark.asyncio
async def test_fetch_events_in_range_without_key_skips_api_call():
    client = MagicMock()
    client.get = AsyncMock()
    provider = RapidApiCalendarProvider(make_settings(rapidapi_calendar_key=""), client)

    events = await provider.fetch_events_in_range(date(2026, 4, 27), date(2026, 5, 3))

    assert events == []
    client.get.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_provider_uses_secondary_when_primary_is_empty():
    fallback_event = EconomicEvent(
        id="fallback",
        time="10:00",
        title="Fallback CPI",
        country="USD",
        currency="USD",
        importance=Importance.MEDIUM,
    )
    primary = MagicMock()
    primary.fetch_events_in_range = AsyncMock(return_value=[])
    fallback = MagicMock()
    fallback.fetch_events_in_range = AsyncMock(return_value=[fallback_event])
    provider = FallbackCalendarProvider(primary=primary, fallback=fallback)

    events = await provider.fetch_events_in_range(date(2026, 4, 27), date(2026, 5, 3))

    assert events == [fallback_event]
    fallback.fetch_events_in_range.assert_awaited_once_with(date(2026, 4, 27), date(2026, 5, 3))


@pytest.mark.asyncio
async def test_fallback_provider_fills_missing_dates_when_primary_is_partial():
    primary_event = EconomicEvent(
        id="primary-monday",
        time="10:00",
        title="Primary CPI",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
        _timestamp=datetime(2026, 4, 27, 10, 0),
    )
    fallback_monday = EconomicEvent(
        id="fallback-monday",
        time="11:00",
        title="Fallback Monday",
        country="US",
        currency="USD",
        importance=Importance.LOW,
        _timestamp=datetime(2026, 4, 27, 11, 0),
    )
    fallback_tuesday = EconomicEvent(
        id="fallback-tuesday",
        time="12:00",
        title="Fallback Tuesday",
        country="US",
        currency="USD",
        importance=Importance.MEDIUM,
        _timestamp=datetime(2026, 4, 28, 12, 0),
    )
    primary = MagicMock()
    primary.fetch_events_in_range = AsyncMock(return_value=[primary_event])
    fallback = MagicMock()
    fallback.fetch_events_in_range = AsyncMock(return_value=[fallback_monday, fallback_tuesday])
    provider = FallbackCalendarProvider(primary=primary, fallback=fallback)

    events = await provider.fetch_events_in_range(date(2026, 4, 27), date(2026, 4, 28))

    assert events == [primary_event, fallback_tuesday]
    fallback.fetch_events_in_range.assert_awaited_once_with(date(2026, 4, 27), date(2026, 4, 28))
