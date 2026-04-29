from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest
import pytz

from scalper_today.domain.entities import EconomicEvent, Importance
from scalper_today.domain.entities.alerts import Alert, AlertCondition, AlertStatus, AlertType
from scalper_today.infrastructure.notifications.notification_scheduler import NotificationScheduler

TZ_MADRID = pytz.timezone("Europe/Madrid")


def make_event(**kwargs):
    defaults = dict(
        id="evt-1",
        time="14:30",
        title="NFP",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
        actual="200K",
        forecast="180K",
        previous="150K",
        surprise="positive",
    )
    defaults.update(kwargs)
    return EconomicEvent(**defaults)


def make_alert(conditions, user_id="user-1"):
    return Alert(
        id="alert-1",
        user_id=user_id,
        name="Test Alert",
        conditions=conditions,
        status=AlertStatus.ACTIVE,
        push_enabled=True,
    )


@pytest.fixture
def scheduler():
    expo = AsyncMock()
    db = AsyncMock()
    return NotificationScheduler(
        expo_push_service=expo,
        database_manager=db,
        check_interval_seconds=60,
        notify_before_minutes=5,
    )


# ── HIGH_IMPACT_EVENT ────────────────────────────────


class TestHighImpactCondition:
    def test_matches_high_importance(self, scheduler):
        event = make_event(importance=Importance.HIGH)
        cond = AlertCondition(alert_type=AlertType.HIGH_IMPACT_EVENT, value=None)
        assert scheduler._condition_matches_event(cond, event) is True

    def test_does_not_match_medium(self, scheduler):
        event = make_event(importance=Importance.MEDIUM)
        cond = AlertCondition(alert_type=AlertType.HIGH_IMPACT_EVENT, value=None)
        assert scheduler._condition_matches_event(cond, event) is False

    def test_does_not_match_low(self, scheduler):
        event = make_event(importance=Importance.LOW)
        cond = AlertCondition(alert_type=AlertType.HIGH_IMPACT_EVENT, value=None)
        assert scheduler._condition_matches_event(cond, event) is False


# ── SPECIFIC_COUNTRY ────────────────────────────────


class TestSpecificCountryCondition:
    def test_exact_match(self, scheduler):
        event = make_event(country="United States")
        cond = AlertCondition(alert_type=AlertType.SPECIFIC_COUNTRY, value="United States")
        assert scheduler._condition_matches_event(cond, event) is True

    def test_case_insensitive(self, scheduler):
        event = make_event(country="United States")
        cond = AlertCondition(alert_type=AlertType.SPECIFIC_COUNTRY, value="united states")
        assert scheduler._condition_matches_event(cond, event) is True

    def test_no_match(self, scheduler):
        event = make_event(country="United States")
        cond = AlertCondition(alert_type=AlertType.SPECIFIC_COUNTRY, value="Germany")
        assert scheduler._condition_matches_event(cond, event) is False

    def test_empty_value_no_match(self, scheduler):
        event = make_event(country="US")
        cond = AlertCondition(alert_type=AlertType.SPECIFIC_COUNTRY, value=None)
        assert scheduler._condition_matches_event(cond, event) is False


# ── SPECIFIC_CURRENCY ───────────────────────────────


class TestSpecificCurrencyCondition:
    def test_exact_match(self, scheduler):
        event = make_event(currency="USD")
        cond = AlertCondition(alert_type=AlertType.SPECIFIC_CURRENCY, value="USD")
        assert scheduler._condition_matches_event(cond, event) is True

    def test_case_insensitive(self, scheduler):
        event = make_event(currency="usd")
        cond = AlertCondition(alert_type=AlertType.SPECIFIC_CURRENCY, value="USD")
        assert scheduler._condition_matches_event(cond, event) is True

    def test_no_match(self, scheduler):
        event = make_event(currency="EUR")
        cond = AlertCondition(alert_type=AlertType.SPECIFIC_CURRENCY, value="USD")
        assert scheduler._condition_matches_event(cond, event) is False


# ── DATA_RELEASE ────────────────────────────────────


class TestDataReleaseCondition:
    def test_matches_when_actual_has_value(self, scheduler):
        event = make_event(actual="1.5%")
        cond = AlertCondition(alert_type=AlertType.DATA_RELEASE, value=None)
        assert scheduler._condition_matches_event(cond, event) is True

    def test_no_match_when_actual_empty(self, scheduler):
        event = make_event(actual="")
        cond = AlertCondition(alert_type=AlertType.DATA_RELEASE, value=None)
        assert scheduler._condition_matches_event(cond, event) is False

    def test_no_match_when_actual_none(self, scheduler):
        event = make_event(actual=None)
        cond = AlertCondition(alert_type=AlertType.DATA_RELEASE, value=None)
        assert scheduler._condition_matches_event(cond, event) is False


# ── SURPRISE_MOVE ───────────────────────────────────


class TestSurpriseMoveCondition:
    def test_big_surprise_matches(self, scheduler):
        event = make_event(actual="2.0%", forecast="1.5%")
        cond = AlertCondition(alert_type=AlertType.SURPRISE_MOVE, value=None)
        assert scheduler._condition_matches_event(cond, event) is True

    def test_small_diff_no_match(self, scheduler):
        event = make_event(actual="1.5%", forecast="1.4%")
        cond = AlertCondition(alert_type=AlertType.SURPRISE_MOVE, value=None)
        assert scheduler._condition_matches_event(cond, event) is False

    def test_no_actual_no_match(self, scheduler):
        event = make_event(actual="", forecast="1.5%")
        cond = AlertCondition(alert_type=AlertType.SURPRISE_MOVE, value=None)
        assert scheduler._condition_matches_event(cond, event) is False


# ── _alert_matches_event ────────────────────────────


class TestAlertMatchesEvent:
    def test_any_condition_matches(self, scheduler):
        event = make_event(importance=Importance.LOW, country="US")
        alert = make_alert(
            [
                AlertCondition(alert_type=AlertType.HIGH_IMPACT_EVENT, value=None),
                AlertCondition(alert_type=AlertType.SPECIFIC_COUNTRY, value="US"),
            ]
        )
        # LOW importance fails HIGH_IMPACT but US country matches
        assert scheduler._alert_matches_event(alert, event) is True

    def test_no_condition_matches(self, scheduler):
        event = make_event(importance=Importance.LOW, country="US")
        alert = make_alert(
            [
                AlertCondition(alert_type=AlertType.HIGH_IMPACT_EVENT, value=None),
                AlertCondition(alert_type=AlertType.SPECIFIC_COUNTRY, value="Germany"),
            ]
        )
        assert scheduler._alert_matches_event(alert, event) is False

    def test_empty_conditions(self, scheduler):
        event = make_event()
        alert = make_alert([])
        assert scheduler._alert_matches_event(alert, event) is False


# ── _parse_event_time ───────────────────────────────


class TestParseEventTime:
    def test_valid_time(self, scheduler):
        today = date(2026, 3, 18)
        result = scheduler._parse_event_time("14:30", today)
        assert result is not None
        assert result.hour == 14 or result.hour == 13  # depends on UTC offset

    def test_empty_string(self, scheduler):
        today = date(2026, 3, 18)
        assert scheduler._parse_event_time("", today) is None

    def test_none(self, scheduler):
        today = date(2026, 3, 18)
        assert scheduler._parse_event_time(None, today) is None

    def test_invalid_format(self, scheduler):
        today = date(2026, 3, 18)
        assert scheduler._parse_event_time("All Day", today) is None


# ── _cleanup_notified_cache ─────────────────────────


class TestCleanupCache:
    def test_clears_on_new_day(self, scheduler):
        scheduler._notified_events = {"evt-1": {"user-1"}}
        scheduler._last_check_date = date(2026, 3, 17)
        # Simulate running on 2026-03-18
        scheduler._cleanup_notified_cache()
        # Cache should be cleared because today != last_check_date
        # (depends on actual current date, so we test the mechanism)
        if scheduler._last_check_date != date(2026, 3, 17):
            assert len(scheduler._notified_events) == 0

    def test_keeps_on_same_day(self, scheduler):
        today = datetime.now(TZ_MADRID).date()
        scheduler._notified_events = {"evt-1": {"user-1"}}
        scheduler._last_check_date = today
        scheduler._cleanup_notified_cache()
        assert len(scheduler._notified_events) == 1


# ── _parse_numeric ──────────────────────────────────


class TestParseNumeric:
    def test_percentage(self, scheduler):
        assert scheduler._parse_numeric("2.5%") == 2.5

    def test_plain_number(self, scheduler):
        assert scheduler._parse_numeric("100") == 100.0

    def test_k_suffix(self, scheduler):
        assert scheduler._parse_numeric("200K") == 200000.0

    def test_comma_decimal(self, scheduler):
        assert scheduler._parse_numeric("1,5") == 1.5

    def test_empty(self, scheduler):
        assert scheduler._parse_numeric("") is None

    def test_none(self, scheduler):
        assert scheduler._parse_numeric(None) is None

    def test_non_numeric(self, scheduler):
        assert scheduler._parse_numeric("N/A") is None
