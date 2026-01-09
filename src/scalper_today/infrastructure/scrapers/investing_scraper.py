import logging
from datetime import datetime
from typing import List, Optional

import httpx
import pytz
from bs4 import BeautifulSoup

from scalper_today.config import Settings
from scalper_today.domain import EconomicEvent, IEventScraper, Importance

logger = logging.getLogger(__name__)


class InvestingComScraper(IEventScraper):
    BROWSER_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.investing.com/economic-calendar/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Cookie": "adBlockerNewUserDomains=1; cal-custom-range=0%200; cal-timezone-offset=0;",
    }

    TZ_MADRID = pytz.timezone("Europe/Madrid")

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._client = http_client

    async def fetch_today_events(self) -> List[EconomicEvent]:
        try:
            raw_html = await self._fetch_calendar_html()
            if not raw_html:
                logger.warning("No HTML received from Investing.com")
                return []
            return self._parse_events(raw_html)
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []

    async def _fetch_calendar_html(self) -> str:
        current_date = datetime.now(self.TZ_MADRID).strftime("%Y-%m-%d")

        payload = {
            "dateFrom": current_date,
            "dateTo": current_date,
            "timeZone": "60",  # Timezone code 60 = Madrid/UTC+1
            "currentTab": "today",
            "limit_from": "0",
        }

        try:
            response = await self._client.post(
                self._settings.investing_api_url,
                data=payload,
                headers=self.BROWSER_HEADERS,
            )

            if response.status_code == 200:
                return response.json().get("data", "")

            logger.error(f"Investing.com returned status {response.status_code}")
            return ""

        except httpx.TimeoutException:
            logger.error("Timeout fetching from Investing.com")
            return ""
        except Exception as e:
            logger.error(f"HTTP error: {e}")
            return ""

    def _parse_events(self, html: str) -> List[EconomicEvent]:
        events: List[EconomicEvent] = []
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("tr.js-event-item")

        logger.info(f"Processing {len(rows)} event rows")
        today = datetime.now(self.TZ_MADRID).date()

        for row in rows:
            try:
                event = self._parse_single_row(row, today)
                if event:
                    events.append(event)
            except Exception as e:
                logger.debug(f"Failed to parse row: {e}")
                continue

        # Sort by: 1) time, 2) country, 3) importance (high to low)
        # Events at the same time are grouped by country, then by importance
        def sort_key(e):
            time_val = e.time if e.time else "99:99"
            country_val = e.country if e.country else "ZZZ"
            # Importance enum: LOW=1, MEDIUM=2, HIGH=3
            # Negate to sort HIGH first: HIGH=-3, MEDIUM=-2, LOW=-1
            importance_order = -e.importance.value
            return (time_val, country_val, importance_order)

        events.sort(key=sort_key)
        return events

    def _parse_single_row(self, row, today) -> Optional[EconomicEvent]:
        # Extract datetime
        event_dt = self._extract_datetime(row, today)
        if not event_dt:
            return None

        # All events are for today (we trust the API's date filter)

        # Event name
        event_cell = row.select_one(".event")
        if not event_cell:
            return None
        event_name = event_cell.get_text(strip=True)
        if not event_name:
            return None

        # URL
        link = row.select_one(".event a")
        url = ""
        if link and link.get("href", "").startswith("/"):
            url = f"https://www.investing.com{link.get('href')}"

        # Importance (stars)
        importance = self._extract_importance(row)

        # Country & Currency
        country, currency = self._extract_location(row)

        # Values
        actual = self._safe_text(row.select_one(".act"))
        forecast = self._safe_text(row.select_one(".fore"))
        previous = self._safe_text(row.select_one(".prev"))

        # Surprise
        surprise = self._extract_surprise(row)

        # Generate a unique ID
        row_id = row.get("id", "") or f"{event_dt.strftime('%H%M')}-{event_name[:10]}"

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

    def _extract_datetime(self, row, today) -> Optional[datetime]:
        # Use time cell - already in Madrid timezone (we requested timezone=88)
        time_cell = row.select_one(".time")
        if time_cell:
            time_text = time_cell.get_text(strip=True)
            if ":" in time_text:
                try:
                    t = datetime.strptime(time_text, "%H:%M")
                    return self.TZ_MADRID.localize(
                        t.replace(year=today.year, month=today.month, day=today.day)
                    )
                except ValueError:
                    pass

        return None

    def _extract_importance(self, row) -> Importance:
        cell = row.select_one(".sentiment")
        if not cell:
            return Importance.LOW

        # Count filled bull icons (updated class names)
        stars = len(cell.select(".grayFullBullishIcon"))

        # Fallback to old class names (backwards compatibility)
        if stars == 0:
            stars = len(cell.select(".grayFullBullIcon")) or len(cell.select(".grayFull"))

        if stars >= 3:
            return Importance.HIGH
        elif stars == 2:
            return Importance.MEDIUM
        return Importance.LOW

    def _extract_location(self, row) -> tuple[str, str]:
        flag = row.select_one(".flagCur")
        if not flag:
            return "Global", ""

        currency = flag.get_text(strip=True).replace("&nbsp;", "")
        country = "Global"

        title_span = flag.select_one("span[title]")
        if title_span:
            country = title_span.get("title", "Global")

        return country, currency

    def _extract_surprise(self, row) -> str:
        act = row.select_one(".act")
        if not act:
            return "neutral"

        classes = act.get("class", [])
        if "greenFont" in classes:
            return "positive"
        elif "redFont" in classes:
            return "negative"
        return "neutral"

    @staticmethod
    def _safe_text(el) -> str:
        return el.get_text(strip=True) if el else ""
