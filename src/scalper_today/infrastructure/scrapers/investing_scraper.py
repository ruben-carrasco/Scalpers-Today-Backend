import asyncio
import logging
import re
from datetime import date, datetime
from typing import List, Optional

import httpx
import pytz
from bs4 import BeautifulSoup, Tag

from scalper_today.config import Settings
from scalper_today.domain import EconomicEvent, IEventScraper, Importance

logger = logging.getLogger(__name__)


class InvestingComScraper(IEventScraper):
    CALENDAR_URL = "https://www.investing.com/economic-calendar/"

    HTML_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    AJAX_HEADERS = {
        **HTML_HEADERS,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.investing.com",
        "Referer": CALENDAR_URL,
        "X-Requested-With": "XMLHttpRequest",
    }

    TZ_MADRID = pytz.timezone("Europe/Madrid")
    MAX_RETRIES = 2
    RETRY_BASE_DELAY_SECONDS = 1

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._client = http_client

    async def fetch_today_events(self) -> List[EconomicEvent]:
        try:
            html = await self.fetch_html()
            events = self.parse_html(html)

            if events:
                logger.info("Parsed events from Investing calendar HTML", extra={"count": len(events)})
                return events

            logger.warning("Calendar HTML returned no parsable events; trying AJAX fallback")
            return await self.fetch_ajax_fallback()
        except Exception as e:
            logger.error("Failed to fetch Investing events", extra={"error": str(e)})
            return []

    async def fetch_html(self) -> str:
        """Primary strategy: fetch full calendar HTML page."""
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await self._client.get(self.CALENDAR_URL, headers=self.HTML_HEADERS)
                if response.status_code == 200:
                    return response.text

                logger.warning(
                    "Investing calendar HTML fetch non-200",
                    extra={"status_code": response.status_code, "attempt": attempt},
                )

                if response.status_code == 403:
                    self._log_forbidden_debug("html", response)

                if 400 <= response.status_code < 500 and response.status_code not in (403, 429):
                    return ""
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning("Timeout fetching Investing HTML", extra={"attempt": attempt})
            except httpx.HTTPError as e:
                last_exception = e
                logger.warning("HTTP error fetching Investing HTML", extra={"attempt": attempt, "error": str(e)})
            except Exception as e:
                last_exception = e
                logger.warning(
                    "Unexpected error fetching Investing HTML",
                    extra={"attempt": attempt, "error": str(e)},
                )

            if attempt < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_BASE_DELAY_SECONDS)

        if last_exception:
            logger.error("Failed to fetch Investing HTML", extra={"error": str(last_exception)})
        return ""

    def parse_html(self, html: str) -> List[EconomicEvent]:
        """Parse event rows from full calendar HTML or AJAX snippet HTML."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        today = datetime.now(self.TZ_MADRID).date()

        events: List[EconomicEvent] = []
        rows = self._select_event_rows(soup)
        logger.info("Processing Investing event rows", extra={"rows": len(rows)})

        for row in rows:
            try:
                event = self._parse_single_row(row, today)
                if event is not None:
                    events.append(event)
            except Exception as e:
                logger.debug("Failed to parse Investing row", extra={"error": str(e)})

        events.sort(key=lambda e: (e.time or "99:99", e.country or "ZZZ", -int(e.importance.value)))
        return events

    async def fetch_ajax_fallback(self) -> List[EconomicEvent]:
        """Fallback strategy: bootstrap session, call AJAX endpoint, parse returned HTML."""
        ajax_html = await self._fetch_calendar_html()
        if not ajax_html:
            return []
        return self.parse_html(ajax_html)

    async def _fetch_calendar_html(self) -> str:
        """Backward-compatible helper: fetch HTML snippet via AJAX endpoint."""
        current_date = datetime.now(self.TZ_MADRID).strftime("%Y-%m-%d")
        payload = {
            "dateFrom": current_date,
            "dateTo": current_date,
            "timeZone": "60",
            "currentTab": "today",
            "limit_from": "0",
        }

        last_exception: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                await self._bootstrap_session()

                response = await self._client.post(
                    self._settings.investing_api_url,
                    data=payload,
                    headers=self.AJAX_HEADERS,
                )

                if response.status_code == 200:
                    data = response.json()
                    html = data.get("data", "") if isinstance(data, dict) else ""
                    return html if isinstance(html, str) else ""

                logger.warning(
                    "Investing AJAX fallback non-200",
                    extra={"status_code": response.status_code, "attempt": attempt},
                )

                if response.status_code == 403:
                    self._log_forbidden_debug("ajax", response)

                if 400 <= response.status_code < 500 and response.status_code not in (403, 429):
                    return ""
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning("Timeout fetching Investing AJAX fallback", extra={"attempt": attempt})
            except httpx.HTTPError as e:
                last_exception = e
                logger.warning(
                    "HTTP error fetching Investing AJAX fallback",
                    extra={"attempt": attempt, "error": str(e)},
                )
            except Exception as e:
                last_exception = e
                logger.warning(
                    "Unexpected error fetching Investing AJAX fallback",
                    extra={"attempt": attempt, "error": str(e)},
                )

            if attempt < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_BASE_DELAY_SECONDS)

        if last_exception:
            logger.error("Failed AJAX fallback for Investing", extra={"error": str(last_exception)})
        return ""

    async def _bootstrap_session(self) -> None:
        """Warm up cookies/session using the calendar page before AJAX call."""
        try:
            response = await self._client.get(self.CALENDAR_URL, headers=self.HTML_HEADERS)
            if response.status_code >= 400:
                logger.debug("Investing session bootstrap non-200", extra={"status_code": response.status_code})
        except Exception as e:
            logger.debug("Investing session bootstrap failed", extra={"error": str(e)})

    def _select_event_rows(self, soup: BeautifulSoup) -> List[Tag]:
        selectors = [
            "tr.js-event-item",
            "tr[data-event-datetime]",
            "table#economicCalendarData tr",
        ]

        candidates: List[Tag] = []
        for selector in selectors:
            candidates.extend([row for row in soup.select(selector) if isinstance(row, Tag)])

        deduped: List[Tag] = []
        seen: set[str] = set()
        for row in candidates:
            key = str(row.get("id") or row.get("data-event-datetime") or hash(str(row)[:120]))
            if key in seen:
                continue
            seen.add(key)

            if row.select_one(".event") is None and row.select_one("td.event") is None:
                continue
            deduped.append(row)

        return deduped

    def _parse_single_row(self, row: Tag, today: date) -> Optional[EconomicEvent]:
        event_dt = self._extract_datetime(row, today)
        if event_dt is None:
            return None

        event_name = self._extract_event_name(row)
        if not event_name:
            return None

        url = self._extract_url(row)
        importance = self._extract_importance(row)
        country, currency = self._extract_location(row)

        actual = self._safe_text(row.select_one(".act"))
        forecast = self._safe_text(row.select_one(".fore"))
        previous = self._safe_text(row.select_one(".prev"))
        surprise = self._extract_surprise(row)

        row_id = self._build_row_id(row, event_dt, event_name, country, currency)

        return EconomicEvent(
            id=row_id,
            time=event_dt.strftime("%H:%M"),
            title=event_name,
            url=url,
            country=country,
            currency=currency,
            importance=importance,
            actual=actual,
            forecast=forecast,
            previous=previous,
            surprise=surprise,
            _timestamp=event_dt,
        )

    def _extract_datetime(self, row: Tag, today: date) -> Optional[datetime]:
        attr_value = row.get("data-event-datetime")
        if isinstance(attr_value, str) and attr_value.strip():
            parsed = self._parse_datetime_value(attr_value.strip())
            if parsed is not None:
                return parsed.astimezone(self.TZ_MADRID)

        time_text = self._extract_time_text(row)
        if not time_text:
            return None

        match = re.search(r"(\d{1,2}:\d{2})", time_text)
        if not match:
            return None

        try:
            parsed_time = datetime.strptime(match.group(1), "%H:%M")
            naive_dt = datetime(
                year=today.year,
                month=today.month,
                day=today.day,
                hour=parsed_time.hour,
                minute=parsed_time.minute,
            )
            return self.TZ_MADRID.localize(naive_dt)
        except ValueError:
            return None

    def _parse_datetime_value(self, value: str) -> Optional[datetime]:
        if value.isdigit():
            try:
                timestamp = int(value)
                if timestamp > 10_000_000_000:
                    timestamp = timestamp // 1000
                return datetime.fromtimestamp(timestamp, tz=self.TZ_MADRID)
            except (ValueError, OSError):
                return None

        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return self.TZ_MADRID.localize(parsed)
            return parsed
        except ValueError:
            pass

        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(value, fmt)
                return self.TZ_MADRID.localize(parsed)
            except ValueError:
                continue

        return None

    def _extract_time_text(self, row: Tag) -> str:
        time_cell = row.select_one(".time") or row.select_one("td.first.left.time")
        return self._safe_text(time_cell)

    def _extract_event_name(self, row: Tag) -> str:
        event_cell = row.select_one(".event") or row.select_one("td.left.event")
        if event_cell is None:
            return ""
        return self._safe_text(event_cell)

    def _extract_url(self, row: Tag) -> str:
        link = row.select_one(".event a") or row.select_one("td.left.event a")
        href = (link.get("href", "") if link else "").strip()
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return f"https://www.investing.com{href}"
        return ""

    def _extract_importance(self, row: Tag) -> Importance:
        cell = row.select_one(".sentiment")
        if cell is None:
            return Importance.LOW

        stars = len(
            cell.select(
                ".grayFullBullishIcon, .grayFullBullIcon, .grayFull, .bullishIcon, i[class*='Bull']"
            )
        )

        if stars >= 3:
            return Importance.HIGH
        if stars == 2:
            return Importance.MEDIUM
        return Importance.LOW

    def _extract_location(self, row: Tag) -> tuple[str, str]:
        flag = row.select_one(".flagCur")
        if flag is None:
            return "Global", ""

        country = "Global"
        title_span = flag.select_one("span[title]")
        if title_span is not None:
            country = str(title_span.get("title", "Global")).strip() or "Global"

        raw_text = self._safe_text(flag)
        currency_match = re.findall(r"\b[A-Z]{3}\b", raw_text)
        currency = currency_match[-1] if currency_match else raw_text

        return country, currency.strip()

    def _extract_surprise(self, row: Tag) -> str:
        act = row.select_one(".act")
        if act is None:
            return "neutral"

        classes = act.get("class", [])
        if "greenFont" in classes:
            return "positive"
        if "redFont" in classes:
            return "negative"
        return "neutral"

    def _build_row_id(
        self,
        row: Tag,
        event_dt: datetime,
        event_name: str,
        country: str,
        currency: str,
    ) -> str:
        row_id = str(row.get("id", "")).strip()
        if row_id:
            return row_id

        slug = re.sub(r"\W+", "-", event_name.lower()).strip("-")[:32]
        location = re.sub(r"\W+", "-", f"{country}-{currency}".lower()).strip("-")[:24]
        return f"{event_dt.strftime('%Y%m%d%H%M')}-{location}-{slug}"

    def _log_forbidden_debug(self, source: str, response: httpx.Response) -> None:
        body_preview = (response.text or "")[:500]
        logger.warning(
            "Investing returned 403",
            extra={"source": source, "status_code": response.status_code},
        )
        logger.debug(
            "Investing 403 details",
            extra={
                "source": source,
                "headers": dict(response.headers),
                "body_preview": body_preview,
            },
        )

    @staticmethod
    def _safe_text(el: Optional[Tag]) -> str:
        if el is None:
            return ""
        text = el.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text).strip()

    # Backward-compatible alias
    def _parse_events(self, html: str) -> List[EconomicEvent]:
        return self.parse_html(html)
