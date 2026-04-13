from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from scalper_today.config import Settings
from scalper_today.domain.entities import Importance
from scalper_today.infrastructure.providers import ForexFactoryCalendarProvider


def make_response(status_code: int = 200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def make_settings(**overrides) -> Settings:
    defaults = {
        "forexfactory_calendar_url": "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_parse_payload_maps_event_fields():
    settings = make_settings()
    provider = ForexFactoryCalendarProvider(settings, MagicMock())
    payload = [
        {
            "title": "CPI y/y",
            "country": "USD",
            "date": "2026-04-13T14:30:00+00:00",
            "impact": "High",
            "actual": "3.2%",
            "forecast": "3.0%",
            "previous": "2.9%",
        }
    ]

    events = provider._parse_payload(payload, date(2026, 4, 13))

    assert len(events) == 1
    event = events[0]
    assert event.title == "CPI y/y"
    assert event.country == "USD"
    assert event.currency == "USD"
    assert event.importance == Importance.HIGH
    assert event.actual == "3.2%"
    assert event.forecast == "3.0%"
    assert event.previous == "2.9%"
    assert event.surprise == "positive"
    assert event.url == settings.forexfactory_calendar_url


def test_parse_payload_fills_missing_data_fields():
    provider = ForexFactoryCalendarProvider(make_settings(), MagicMock())
    payload = [
        {
            "title": "Industrial Production m/m",
            "country": "",
            "date": "2026-04-13T08:00:00+00:00",
            "impact": "Medium",
            "actual": "",
            "forecast": "",
            "previous": "",
        }
    ]

    events = provider._parse_payload(payload, date(2026, 4, 13))

    assert len(events) == 1
    event = events[0]
    assert event.country == "N/A"
    assert event.currency == "N/A"
    assert event.actual == "N/A"
    assert event.forecast == "N/A"
    assert event.previous == "N/A"


@pytest.mark.asyncio
async def test_fetch_today_events_returns_empty_on_401():
    client = MagicMock()
    client.get = AsyncMock(return_value=make_response(status_code=401, json_data={"error": "auth"}))
    provider = ForexFactoryCalendarProvider(make_settings(), client)

    events = await provider.fetch_today_events()

    assert events == []
    assert client.get.call_count == 1


@pytest.mark.asyncio
async def test_fetch_retries_on_timeout():
    client = MagicMock()
    client.get = AsyncMock(
        side_effect=[
            httpx.TimeoutException("timeout"),
            make_response(status_code=200, json_data=[]),
        ]
    )
    provider = ForexFactoryCalendarProvider(make_settings(), client)

    with patch(
        "scalper_today.infrastructure.providers.forexfactory_calendar_provider.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        events = await provider.fetch_today_events()

    assert events == []
    assert client.get.call_count == 2
