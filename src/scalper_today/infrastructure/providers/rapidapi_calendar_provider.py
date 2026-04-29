import logging
import re
from datetime import date, datetime
from typing import Any

import httpx
import pytz

from scalper_today.config import Settings
from scalper_today.domain.entities import EconomicEvent, Importance
from scalper_today.domain.interfaces import IEventProvider

logger = logging.getLogger(__name__)


class RapidApiCalendarProvider(IEventProvider):
    TZ_MADRID = pytz.timezone("Europe/Madrid")
    MISSING_FIELD_VALUE = "N/A"

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._client = http_client

    async def fetch_today_events(self) -> list[EconomicEvent]:
        target_date = datetime.now(self.TZ_MADRID).date()
        return await self.fetch_events_in_range(target_date, target_date)

    async def fetch_events_in_range(self, start_date: date, end_date: date) -> list[EconomicEvent]:
        payload = await self._fetch_payload(start_date, end_date)
        if payload is None:
            return []
        return self._parse_payload(payload, start_date, end_date)

    async def _fetch_payload(self, start_date: date, end_date: date) -> Any | None:
        if not self._settings.rapidapi_calendar_key:
            logger.warning("RapidAPI calendar key is not configured")
            return None

        try:
            response = await self._client.get(
                self._settings.rapidapi_calendar_url,
                headers={
                    "X-RapidAPI-Key": self._settings.rapidapi_calendar_key,
                    "X-RapidAPI-Host": self._settings.rapidapi_calendar_host,
                    "Accept": "application/json",
                },
                params={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "timezone": self._settings.rapidapi_calendar_timezone,
                    "limit": self._settings.rapidapi_calendar_limit,
                },
            )
            if response.status_code == 200:
                return response.json()

            logger.warning(
                "RapidAPI calendar request non-200",
                extra={"status_code": response.status_code},
            )
            return None
        except httpx.HTTPError as exc:
            logger.warning("HTTP error fetching RapidAPI calendar", extra={"error": str(exc)})
            return None

    def _parse_payload(self, payload: Any, start_date: date, end_date: date) -> list[EconomicEvent]:
        rows = self._extract_rows(payload)
        events_by_id: dict[str, EconomicEvent] = {}

        for row in rows:
            if not isinstance(row, dict):
                continue
            event = self._to_event(row, start_date, end_date)
            if event is not None:
                events_by_id[event.id] = event

        events = list(events_by_id.values())
        events.sort(
            key=lambda event: (
                event._timestamp.isoformat() if event._timestamp else "",
                event.time or "99:99",
                event.country or "ZZZ",
                -int(event.importance.value),
            )
        )
        logger.info("Parsed events from RapidAPI calendar", extra={"count": len(events)})
        return events

    @staticmethod
    def _extract_rows(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        for key in ("data", "events", "calendar", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return []

    def _to_event(
        self, row: dict[str, Any], start_date: date, end_date: date
    ) -> EconomicEvent | None:
        title = self._first_text(row, "title", "event", "name", "indicator")
        if not title:
            return None

        event_dt = self._extract_datetime(row)
        if event_dt is None:
            return None

        event_date = event_dt.date()
        if event_date < start_date or event_date > end_date:
            return None

        currency = self._first_text(row, "currencyCode", "currency", "countryCode", "country")
        country = (
            self._first_text(row, "countryCode", "country", "currencyCode", "currency") or currency
        )
        actual = self._data_value(self._first_value(row, "actual", "actualValue"))
        forecast = self._data_value(
            self._first_value(row, "forecast", "consensus", "estimate", "expected")
        )
        previous = self._data_value(self._first_value(row, "previous", "previousValue", "revised"))
        importance = Importance(self._extract_importance(row))
        surprise = self._extract_surprise(actual, forecast, row.get("isBetterThanExpected"))
        event_id = self._build_event_id(row, event_dt, title, country, currency)

        return EconomicEvent(
            id=event_id,
            time=event_dt.strftime("%H:%M"),
            title=title,
            country=country or self.MISSING_FIELD_VALUE,
            currency=currency or self.MISSING_FIELD_VALUE,
            importance=importance,
            actual=actual,
            forecast=forecast,
            previous=previous,
            surprise=surprise,
            url=self._settings.rapidapi_calendar_url,
            _timestamp=event_dt,
        )

    def _extract_datetime(self, row: dict[str, Any]) -> datetime | None:
        raw_value = self._first_value(row, "dateUtc", "date", "datetime", "timestamp", "time")
        parsed = self._parse_datetime(raw_value)
        if parsed is not None:
            return parsed

        date_text = self._first_text(row, "date")
        time_text = self._first_text(row, "time")
        if not date_text or not time_text:
            return None
        return self._parse_datetime(f"{date_text}T{time_text}")

    def _parse_datetime(self, raw_value: Any) -> datetime | None:
        text = self._safe_text(raw_value)
        if not text:
            return None

        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return self.TZ_MADRID.localize(parsed)
        return parsed.astimezone(self.TZ_MADRID)

    def _extract_importance(self, row: dict[str, Any]) -> int:
        text = self._first_text(row, "volatility", "importance", "impact", "priority").lower()
        if "high" in text or text == "3":
            return 3
        if "medium" in text or "moderate" in text or text == "2":
            return 2
        if "low" in text or text == "1":
            return 1
        return 2

    def _extract_surprise(self, actual: str, forecast: str, is_better: Any) -> str:
        if isinstance(is_better, bool):
            return "positive" if is_better else "negative"

        actual_num = self._parse_number(actual)
        forecast_num = self._parse_number(forecast)
        if actual_num is None or forecast_num is None:
            return "neutral"
        if actual_num > forecast_num:
            return "positive"
        if actual_num < forecast_num:
            return "negative"
        return "neutral"

    @staticmethod
    def _parse_number(raw: str) -> float | None:
        if not raw:
            return None
        text = raw.replace(",", "").replace(" ", "").strip().upper()
        match = re.search(r"[-+]?\d*\.?\d+", text)
        if not match:
            return None

        value = float(match.group(0))
        if "K" in text:
            value *= 1_000
        elif "M" in text:
            value *= 1_000_000
        elif "B" in text:
            value *= 1_000_000_000
        return value

    @staticmethod
    def _build_event_id(
        row: dict[str, Any], event_dt: datetime, title: str, country: str, currency: str
    ) -> str:
        provider_id = RapidApiCalendarProvider._safe_text(row.get("id") or row.get("eventId"))
        if provider_id:
            return f"rapidapi-{provider_id}"[:100]

        time_part = event_dt.strftime("%Y%m%d-%H%M")
        title_slug = re.sub(r"\W+", "-", title.lower()).strip("-")[:34]
        location_slug = re.sub(r"\W+", "-", f"{country}-{currency}".lower()).strip("-")[:24]
        return f"rapidapi-{time_part}-{location_slug}-{title_slug}"[:100]

    @staticmethod
    def _first_value(row: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = row.get(key)
            if value is not None:
                return value
        return None

    @classmethod
    def _first_text(cls, row: dict[str, Any], *keys: str) -> str:
        for key in keys:
            text = cls._safe_text(row.get(key))
            if text:
                return text
        return ""

    @staticmethod
    def _safe_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _data_value(self, value: Any) -> str:
        text = self._safe_text(value)
        return text if text else self.MISSING_FIELD_VALUE
