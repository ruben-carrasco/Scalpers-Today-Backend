import asyncio
import logging
import re
from datetime import date, datetime, time, timezone
from typing import Any, Iterable, Optional

import httpx
import pytz

from scalper_today.config import Settings
from scalper_today.domain.entities import EconomicEvent, Importance
from scalper_today.domain.interfaces import IEventScraper

logger = logging.getLogger(__name__)


class FmpCalendarProvider(IEventScraper):
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
        params = {
            "from": target_date.isoformat(),
            "to": target_date.isoformat(),
            "apikey": self._settings.fmp_api_key,
        }

        last_exception: Optional[Exception] = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await self._client.get(
                    self._settings.fmp_calendar_url,
                    params=params,
                    headers=self.HEADERS,
                )
                if response.status_code == 200:
                    return response.json()

                logger.warning(
                    "FMP calendar request non-200",
                    extra={"status_code": response.status_code, "attempt": attempt},
                )
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    return None
            except httpx.TimeoutException as exc:
                last_exception = exc
                logger.warning("Timeout fetching FMP calendar", extra={"attempt": attempt})
            except httpx.HTTPError as exc:
                last_exception = exc
                logger.warning(
                    "HTTP error fetching FMP calendar",
                    extra={"attempt": attempt, "error": str(exc)},
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                last_exception = exc
                logger.error(
                    "Unexpected error fetching FMP calendar",
                    extra={"attempt": attempt, "error": str(exc)},
                )

            if attempt < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_BASE_DELAY_SECONDS)

        if last_exception:
            logger.error("Failed to fetch FMP calendar", extra={"error": str(last_exception)})
        return None

    def _parse_payload(self, payload: Any, target_date: date) -> list[EconomicEvent]:
        rows = self._extract_rows(payload)
        events_by_id: dict[str, EconomicEvent] = {}

        for row in rows:
            if not isinstance(row, dict):
                continue
            event = self._to_event(row, target_date)
            if event is not None:
                events_by_id[event.id] = event

        events = list(events_by_id.values())
        events.sort(key=lambda e: (e.time or "99:99", e.country or "ZZZ", -int(e.importance.value)))
        logger.info("Parsed events from FMP calendar", extra={"count": len(events)})
        return events

    @staticmethod
    def _extract_rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if isinstance(payload, dict):
            for key in ("economicCalendar", "calendar", "data", "results", "events"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    def _to_event(self, row: dict[str, Any], target_date: date) -> Optional[EconomicEvent]:
        title = self._pick_first(
            row,
            ("event", "indicator", "title", "name", "category", "eventName"),
        )
        if not title:
            return None

        event_dt = self._extract_datetime(row, target_date)
        time_text = event_dt.strftime("%H:%M")

        country = self._pick_first(
            row,
            ("country", "countryName", "country_name", "region", "zone"),
            default="Global",
        )
        currency = self._pick_first(row, ("currency", "currencyCode", "currency_code", "ccy"))

        actual = self._pick_first(row, ("actual",), default="")
        forecast = self._pick_first(row, ("forecast", "estimate", "consensus"), default="")
        previous = self._pick_first(row, ("previous", "prior"), default="")

        importance = Importance(self._extract_importance(row))
        surprise = self._extract_surprise(row, actual, forecast)

        url = self._pick_first(row, ("url", "link", "sourceUrl", "source"), default="")
        event_id = self._build_event_id(event_dt, title, country, currency)

        return EconomicEvent(
            id=event_id,
            time=time_text,
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

    def _extract_datetime(self, row: dict[str, Any], target_date: date) -> datetime:
        for key in ("date", "datetime", "eventDate", "releaseDate", "timestamp"):
            value = row.get(key)
            parsed = self._parse_datetime(value, target_date)
            if parsed is not None:
                return parsed

        raw_time = self._pick_first(row, ("time",), default="00:00")
        parsed_time = self._parse_time(raw_time)
        return self.TZ_MADRID.localize(datetime.combine(target_date, parsed_time))

    def _parse_datetime(self, value: Any, target_date: date) -> Optional[datetime]:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone(
                    self.TZ_MADRID
                )
            except (OverflowError, OSError, ValueError):
                return None

        text = str(value).strip()
        if not text:
            return None

        if re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", text):
            parsed_time = self._parse_time(text)
            return self.TZ_MADRID.localize(datetime.combine(target_date, parsed_time))

        iso_candidate = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(iso_candidate)
            if parsed.tzinfo is None:
                return self.TZ_MADRID.localize(parsed)
            return parsed.astimezone(self.TZ_MADRID)
        except ValueError:
            pass

        formats = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%m/%d/%Y %H:%M",
            "%d-%m-%Y %H:%M",
            "%m-%d-%Y %H:%M",
        )
        for fmt in formats:
            try:
                parsed = datetime.strptime(text, fmt)
                return self.TZ_MADRID.localize(parsed)
            except ValueError:
                continue

        return None

    @staticmethod
    def _parse_time(value: str) -> time:
        try:
            parts = value.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            second = int(parts[2]) if len(parts) > 2 else 0
            return time(hour=hour, minute=minute, second=second)
        except (ValueError, IndexError):
            return time(0, 0)

    @staticmethod
    def _extract_importance(row: dict[str, Any]) -> int:
        raw = row.get("importance", row.get("impact", row.get("importanceLevel", "")))
        if isinstance(raw, bool):
            return 1
        if isinstance(raw, int):
            return max(1, min(3, raw))
        if isinstance(raw, float):
            return max(1, min(3, int(raw)))

        text = str(raw).strip().lower()
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

    def _extract_surprise(self, row: dict[str, Any], actual: str, forecast: str) -> str:
        raw_surprise = (
            str(row.get("surprise", row.get("signal", row.get("sentiment", "")))).strip().lower()
        )
        if raw_surprise in {"positive", "negative", "neutral"}:
            return raw_surprise
        if "pos" in raw_surprise:
            return "positive"
        if "neg" in raw_surprise:
            return "negative"

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
    def _pick_first(row: dict[str, Any], keys: Iterable[str], default: str = "") -> str:
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return default

    @staticmethod
    def _build_event_id(event_dt: datetime, title: str, country: str, currency: str) -> str:
        time_part = event_dt.strftime("%Y%m%d-%H%M")
        title_slug = re.sub(r"\W+", "-", title.lower()).strip("-")[:34]
        location_slug = re.sub(r"\W+", "-", f"{country}-{currency}".lower()).strip("-")[:24]
        event_id = f"fmp-{time_part}-{location_slug}-{title_slug}"
        return event_id[:100]
