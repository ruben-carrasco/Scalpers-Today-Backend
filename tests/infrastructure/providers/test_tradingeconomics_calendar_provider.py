from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from scalper_today.config import Settings
from scalper_today.domain.entities import Importance
from scalper_today.infrastructure.providers import TradingEconomicsCalendarProvider


def make_response(status_code: int = 200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    return response


def make_settings(**overrides) -> Settings:
    defaults = {"tradingeconomics_api_key": "guest:guest"}
    defaults.update(overrides)
    return Settings(**defaults)


def test_parse_payload_maps_event_fields():
    provider = TradingEconomicsCalendarProvider(make_settings(), MagicMock())
    payload = [
        {
            "CalendarId": "123",
            "Date": "2026-04-13T14:30:00",
            "Country": "United States",
            "Currency": "USD",
            "Event": "Non Farm Payrolls",
            "Actual": "225K",
            "Forecast": "180K",
            "Previous": "150K",
            "Importance": "High",
            "URL": "https://example.com/nfp",
        }
    ]

    events = provider._parse_payload(payload, date(2026, 4, 13))

    assert len(events) == 1
    event = events[0]
    assert event.id == "te-123"
    assert event.title == "Non Farm Payrolls"
    assert event.country == "United States"
    assert event.currency == "USD"
    assert event.importance == Importance.HIGH
    assert event.actual == "225K"
    assert event.forecast == "180K"
    assert event.previous == "150K"
    assert event.surprise == "positive"


@pytest.mark.asyncio
async def test_fetch_today_events_returns_empty_on_401():
    client = MagicMock()
    client.get = AsyncMock(return_value=make_response(status_code=401, json_data={"error": "auth"}))
    provider = TradingEconomicsCalendarProvider(make_settings(), client)

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
    provider = TradingEconomicsCalendarProvider(make_settings(), client)

    with patch(
        "scalper_today.infrastructure.providers.tradingeconomics_calendar_provider.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        events = await provider.fetch_today_events()

    assert events == []
    assert client.get.call_count == 2
