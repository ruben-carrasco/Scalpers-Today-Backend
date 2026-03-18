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


def test_execute_with_empty_events():
    usecase = GetHomeSummaryUseCase()
    briefing = DailyBriefing(
        general_outlook="Quiet day",
        impacted_assets=[],
        cautionary_hours=[],
        statistics=BriefingStats(sentiment="NEUTRAL", volatility_level="LOW"),
    )

    tz_madrid = pytz.timezone("Europe/Madrid")
    fixed_now = datetime(2026, 3, 18, 10, 0, tzinfo=tz_madrid)

    summary = usecase.execute([], briefing, now=fixed_now)

    assert summary.total_events == 0
    assert summary.high_impact_count == 0
    assert summary.medium_impact_count == 0
    assert summary.low_impact_count == 0
    assert summary.next_event is None
    assert summary.highlights == []


def test_greeting_morning():
    assert GetHomeSummaryUseCase.get_greeting(0) == "Buenos días"
    assert GetHomeSummaryUseCase.get_greeting(6) == "Buenos días"
    assert GetHomeSummaryUseCase.get_greeting(11) == "Buenos días"


def test_greeting_afternoon():
    assert GetHomeSummaryUseCase.get_greeting(12) == "Buenas tardes"
    assert GetHomeSummaryUseCase.get_greeting(15) == "Buenas tardes"
    assert GetHomeSummaryUseCase.get_greeting(19) == "Buenas tardes"


def test_greeting_night():
    assert GetHomeSummaryUseCase.get_greeting(20) == "Buenas noches"
    assert GetHomeSummaryUseCase.get_greeting(23) == "Buenas noches"


def test_next_event_none_when_all_past():
    usecase = GetHomeSummaryUseCase()
    events = [
        EconomicEvent(id="1", time="08:00", title="Past 1", country="US", currency="USD", importance=Importance.HIGH),
        EconomicEvent(id="2", time="09:00", title="Past 2", country="EU", currency="EUR", importance=Importance.MEDIUM),
    ]

    result = usecase.find_next_upcoming(events, "22:00")
    assert result is None


def test_next_event_picks_first_upcoming():
    usecase = GetHomeSummaryUseCase()
    events = [
        EconomicEvent(id="1", time="08:00", title="Past", country="US", currency="USD", importance=Importance.LOW),
        EconomicEvent(id="2", time="14:00", title="Next", country="US", currency="USD", importance=Importance.HIGH),
        EconomicEvent(id="3", time="16:00", title="Later", country="EU", currency="EUR", importance=Importance.HIGH),
    ]

    result = usecase.find_next_upcoming(events, "12:00")
    assert result is not None
    assert result.id == "2"


def test_highlights_fallback_to_medium():
    usecase = GetHomeSummaryUseCase()
    events = [
        EconomicEvent(id="1", time="10:00", title="Med 1", country="US", currency="USD", importance=Importance.MEDIUM),
        EconomicEvent(id="2", time="11:00", title="Med 2", country="EU", currency="EUR", importance=Importance.MEDIUM),
        EconomicEvent(id="3", time="12:00", title="Low 1", country="UK", currency="GBP", importance=Importance.LOW),
    ]

    highlights = usecase.generate_highlights(events)
    assert len(highlights) == 2
    assert all(int(h.importance) == 2 for h in highlights)


def test_highlights_max_three():
    usecase = GetHomeSummaryUseCase()
    events = [
        EconomicEvent(id=str(i), time=f"1{i}:00", title=f"High {i}", country="US", currency="USD", importance=Importance.HIGH)
        for i in range(5)
    ]

    highlights = usecase.generate_highlights(events)
    assert len(highlights) == 3
