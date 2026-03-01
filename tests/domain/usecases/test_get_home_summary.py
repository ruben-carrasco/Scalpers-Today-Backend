from datetime import datetime
import pytz

from scalper_today.domain.usecases import GetHomeSummaryUseCase
from scalper_today.domain.entities import EconomicEvent
from scalper_today.domain.entities import Importance
from scalper_today.domain.entities import DailyBriefing
from scalper_today.domain.entities import BriefingStats


def test_get_greeting():
    usecase = GetHomeSummaryUseCase()
    assert usecase.get_greeting(9) == "Buenos días"
    assert usecase.get_greeting(11) == "Buenos días"
    assert usecase.get_greeting(14) == "Buenas tardes"
    assert usecase.get_greeting(19) == "Buenas tardes"
    assert usecase.get_greeting(21) == "Buenas noches"
    assert usecase.get_greeting(23) == "Buenas noches"


def test_count_by_importance():
    events = [
        EconomicEvent(
            id="1",
            time="10:00",
            title="E1",
            country="US",
            currency="USD",
            importance=Importance.LOW,
        ),
        EconomicEvent(
            id="2",
            time="10:00",
            title="E2",
            country="US",
            currency="USD",
            importance=Importance.MEDIUM,
        ),
        EconomicEvent(
            id="3",
            time="10:00",
            title="E3",
            country="US",
            currency="USD",
            importance=Importance.HIGH,
        ),
        EconomicEvent(
            id="4",
            time="10:00",
            title="E4",
            country="US",
            currency="USD",
            importance=Importance.HIGH,
        ),
    ]
    usecase = GetHomeSummaryUseCase()
    high, medium, low = usecase.count_by_importance(events)

    assert high == 2
    assert medium == 1
    assert low == 1


def test_execute_home_summary():
    usecase = GetHomeSummaryUseCase()

    # Mock data
    events = [
        EconomicEvent(
            id="1",
            time="08:00",
            title="Old Event",
            country="EU",
            currency="EUR",
            importance=Importance.MEDIUM,
        ),
        EconomicEvent(
            id="2",
            time="15:00",
            title="Upcoming Event",
            country="US",
            currency="USD",
            importance=Importance.HIGH,
        ),
    ]

    briefing = DailyBriefing(
        general_outlook="Market is volatile",
        impacted_assets=[],
        cautionary_hours=[],
        statistics=BriefingStats(sentiment="BULLISH", volatility_level="HIGH"),
    )

    # Force a specific "now" time
    tz_madrid = pytz.timezone("Europe/Madrid")
    fixed_now = datetime(2026, 3, 9, 12, 30, tzinfo=tz_madrid)

    summary = usecase.execute(events, briefing, now=fixed_now)

    assert summary.greeting == "Buenas tardes"  # 12:30 is afternoon
    assert summary.total_events == 2
    assert summary.high_impact_count == 1
    assert summary.next_event is not None
    assert summary.next_event.title == "Upcoming Event"
    assert summary.sentiment == "BULLISH"
    assert summary.volatility_level == "HIGH"

    # Check highlights (should contain the high impact event)
    assert len(summary.highlights) == 1
    assert summary.highlights[0].id == "2"
