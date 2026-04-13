import asyncio
import logging
import re
from datetime import date, datetime, time
from typing import Any, Optional

import httpx
import pytz

from scalper_today.config import Settings
from scalper_today.domain.entities import EconomicEvent, Importance
from scalper_today.domain.interfaces import IEventScraper

logger = logging.getLogger(__name__)


class TradingEconomicsCalendarProvider(IEventScraper):
    TZ_MADRID = pytz.timezone("Europe/Madrid")
    MAX_RETRIES = 2
    RETRY_BASE_DELAY_SECONDS = 1

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._client = http_client

    async def fetch_today_events(self) -> list[EconomicEvent]:
        target_date = datetime.now(self.TZ_MADRID).date()
        payload = await self._fetch_payload(target_date)
        if payload is None:
            return []
        return self._parse_payload(payload, target_date)

    async def _fetch_payload(self, target_date: date) -> Optional[Any]:
        base_url = self._settings.tradingeconomics_calendar_url.rstrip("/")
        date_fragment = target_date.isoformat()
        url = f"{base_url}/{date_fragment}/{date_fragment}"
        params = {
            "c": self._settings.tradingeconomics_api_key,
            "f": "json",
        }

        last_exception: Optional[Exception] = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await self._client.get(url, params=params, headers=self.HEADERS)
                if response.status_code == 200:
                    return response.json()

                logger.warning(
                    "TradingEconomics calendar request non-200",
                    extra={"status_code": response.status_code, "attempt": attempt},
                )
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    return None
            except httpx.TimeoutException as exc:
                last_exception = exc
                logger.warning(
                    "Timeout fetching TradingEconomics calendar", extra={"attempt": attempt}
                )
            except httpx.HTTPError as exc:
                last_exception = exc
                logger.warning(
                    "HTTP error fetching TradingEconomics calendar",
                    extra={"attempt": attempt, "error": str(exc)},
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                last_exception = exc
                logger.error(
                    "Unexpected error fetching TradingEconomics calendar",
                    extra={"attempt": attempt, "error": str(exc)},
                )

            if attempt < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_BASE_DELAY_SECONDS)

        if last_exception:
            logger.error(
                "Failed to fetch TradingEconomics calendar",
                extra={"error": str(last_exception)},
            )
        return None

    def _parse_payload(self, payload: Any, target_date: date) -> list[EconomicEvent]:
        if not isinstance(payload, list):
            return []

        events_by_id: dict[str, EconomicEvent] = {}
        for row in payload:
            if not isinstance(row, dict):
                continue
            event = self._to_event(row, target_date)
            if event is not None:
                events_by_id[event.id] = event

        events = list(events_by_id.values())
        events.sort(key=lambda e: (e.time or "99:99", e.country or "ZZZ", -int(e.importance.value)))
        logger.info("Parsed events from TradingEconomics", extra={"count": len(events)})
        return events

    def _to_event(self, row: dict[str, Any], target_date: date) -> Optional[EconomicEvent]:
        title = self._safe_text(row.get("Event"))
        if not title:
            return None

        event_dt = self._extract_datetime(row.get("Date"), target_date)
        if event_dt.date() != target_date:
            return None

        country = self._safe_text(row.get("Country")) or "Global"
        currency = self._safe_text(row.get("Currency"))
        actual = self._safe_text(row.get("Actual"))
        forecast = self._safe_text(row.get("Forecast"))
        previous = self._safe_text(row.get("Previous"))
        importance = Importance(self._extract_importance(row.get("Importance")))
        surprise = self._extract_surprise(actual, forecast)
        url = self._safe_text(row.get("URL"))

        raw_id = self._safe_text(row.get("CalendarId"))
        event_id = raw_id if raw_id else self._build_event_id(event_dt, title, country, currency)

        return EconomicEvent(
            id=f"te-{event_id}"[:100],
            time=event_dt.strftime("%H:%M"),
            title=title,
            country=country,
            currency=currency,
            importance=importance,
            actual=actual,
            forecast=forecast,
            previous=previous,
            surprise=surprise,
            url=url,
            _timestamp=event_dt,
        )

    def _extract_datetime(self, raw_value: Any, target_date: date) -> datetime:
        text = self._safe_text(raw_value)
        if not text:
            return self.TZ_MADRID.localize(datetime.combine(target_date, time(0, 0)))

        iso_candidate = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(iso_candidate)
            if parsed.tzinfo is None:
                return self.TZ_MADRID.localize(parsed)
            return parsed.astimezone(self.TZ_MADRID)
        except ValueError:
            pass

        formats = (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %I:%M:%S %p",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
        )
        for fmt in formats:
            try:
                parsed = datetime.strptime(text, fmt)
                return self.TZ_MADRID.localize(parsed)
            except ValueError:
                continue

        return self.TZ_MADRID.localize(datetime.combine(target_date, time(0, 0)))

    @staticmethod
    def _extract_importance(raw: Any) -> int:
        if isinstance(raw, int):
            return max(1, min(3, raw))
        if isinstance(raw, float):
            return max(1, min(3, int(raw)))

        text = str(raw or "").strip().lower()
        if not text:
            return 2

        if any(word in text for word in ("high", "alto", "3")):
            return 3
        if any(word in text for word in ("medium", "moderate", "medio", "2")):
            return 2
        if any(word in text for word in ("low", "bajo", "1")):
            return 1

        bull_count = len(re.findall(r"(bull|★|⭐)", text))
        if bull_count >= 3:
            return 3
        if bull_count == 2:
            return 2
        if bull_count == 1:
            return 1
        return 2

    def _extract_surprise(self, actual: str, forecast: str) -> str:
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
    def _parse_number(raw: str) -> Optional[float]:
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
    def _build_event_id(event_dt: datetime, title: str, country: str, currency: str) -> str:
        time_part = event_dt.strftime("%Y%m%d-%H%M")
        title_slug = re.sub(r"\W+", "-", title.lower()).strip("-")[:34]
        location_slug = re.sub(r"\W+", "-", f"{country}-{currency}".lower()).strip("-")[:24]
        event_id = f"{time_part}-{location_slug}-{title_slug}"
        return event_id[:100]

    @staticmethod
    def _safe_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()
