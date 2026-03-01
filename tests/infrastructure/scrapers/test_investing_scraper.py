import pytest
from datetime import datetime
import pytz
from scalper_today.infrastructure.scrapers.investing_scraper import InvestingComScraper
from scalper_today.domain.entities import Importance


@pytest.fixture
def scraper(mock_ai_analyzer):  # ai analyzer is a mock from conftest
    from scalper_today.config import get_settings
    import httpx

    return InvestingComScraper(get_settings(), httpx.AsyncClient())


def test_parse_single_row_success(scraper):
    # Sample HTML snippet based on real Investing.com structure
    html = """
    <tr class="js-event-item" id="event_123">
        <td class="time">14:30</td>
        <td class="flagCur"><span class="flagIcon" title="United States"></span>USD</td>
        <td class="sentiment"><i class="grayFullBullishIcon"></i><i class="grayFullBullishIcon"></i><i class="grayFullBullishIcon"></i></td>
        <td class="event"><a href="/economic-calendar/nfp-123">Non Farm Payrolls</a></td>
        <td class="act greenFont">200K</td>
        <td class="fore">180K</td>
        <td class="prev">150K</td>
    </tr>
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    row = soup.select_one("tr")

    today = datetime.now(pytz.timezone("Europe/Madrid")).date()
    event = scraper._parse_single_row(row, today)

    assert event is not None
    assert event.id == "event_123"
    assert event.time == "14:30"
    assert event.title == "Non Farm Payrolls"
    assert event.country == "United States"
    assert event.currency == "USD"
    assert event.importance == Importance.HIGH  # 3 bulls
    assert event.actual == "200K"
    assert event.forecast == "180K"
    assert event.previous == "150K"
    assert event.surprise == "positive"  # greenFont


def test_parse_low_importance(scraper):
    html = """
    <tr class="js-event-item">
        <td class="time">10:00</td>
        <td class="flagCur">EUR</td>
        <td class="sentiment"><i class="grayFullBullishIcon"></i></td>
        <td class="event">Low impact talk</td>
        <td class="act"></td><td class="fore"></td><td class="prev"></td>
    </tr>
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    row = soup.select_one("tr")

    today = datetime.now(pytz.timezone("Europe/Madrid")).date()
    event = scraper._parse_single_row(row, today)

    assert event.importance == Importance.LOW
