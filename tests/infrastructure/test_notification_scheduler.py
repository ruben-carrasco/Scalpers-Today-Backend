from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

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
def mock_expo():
    service = AsyncMock()
    service.send_event_alert.return_value = MagicMock(success_count=1, failure_count=0)
    return service


@pytest.fixture
def mock_db_manager():
    manager = MagicMock()
    # mock_session will be used in async with
    mock_session = AsyncMock()
    manager.session.return_value.__aenter__.return_value = mock_session
    return manager


@pytest.fixture
def scheduler(mock_expo, mock_db_manager):
    return NotificationScheduler(
        expo_push_service=mock_expo,
        database_manager=mock_db_manager,
        check_interval_seconds=60,
        notify_before_minutes=5,
    )


@pytest.mark.asyncio
async def test_scheduler_matches_and_notifies(scheduler, mock_expo, mock_db_manager):
    # Setup: Event in 3 minutes (within the 5min window)
    now_madrid = datetime.now(pytz.timezone("Europe/Madrid"))
    event_time_madrid = (now_madrid + timedelta(minutes=3)).strftime("%H:%M")

    event = EconomicEvent(
        id="event-1",
        time=event_time_madrid,
        title="Test Event",
        country="United States",
        currency="USD",
        importance=Importance.HIGH,
        _timestamp=now_madrid + timedelta(minutes=3),
    )

    alert = Alert(
        id="alert-1",
        user_id="user-1",
        name="High Impact Alert",
        conditions=[AlertCondition(alert_type=AlertType.HIGH_IMPACT_EVENT, value=None)],
        push_enabled=True,
    )

    # Mock Repositories
    with (
        patch("scalper_today.infrastructure.database.EventRepository") as MockEventRepo,
        patch(
            "scalper_today.infrastructure.database.repositories.AlertRepository"
        ) as MockAlertRepo,
        patch(
            "scalper_today.infrastructure.database.repositories.DeviceTokenRepository"
        ) as MockDeviceRepo,
    ):
        MockEventRepo.return_value.get_events_by_date = AsyncMock(return_value=[event])
        MockAlertRepo.return_value.get_active_alerts = AsyncMock(return_value=[alert])
        MockAlertRepo.return_value.update = AsyncMock()
        MockDeviceRepo.return_value.get_by_user_id = AsyncMock(
            return_value=[MagicMock(token="token-123")]
        )

        await scheduler._check_and_notify()

        # Verify notification was sent
        mock_expo.send_event_alert.assert_awaited_once()
        assert "event-1" in scheduler._notified_events
        assert "user-1" in scheduler._notified_events["event-1"]


@pytest.mark.asyncio
async def test_scheduler_avoids_duplicate_notifications(scheduler, mock_expo, mock_db_manager):
    # Manually mark as notified
    scheduler._notified_events["event-1"] = {"user-1"}

    now_madrid = datetime.now(pytz.timezone("Europe/Madrid"))
    event_time = (now_madrid + timedelta(minutes=2)).strftime("%H:%M")
    event = EconomicEvent(
        id="event-1",
        time=event_time,
        title="T",
        country="C",
        currency="C",
        importance=Importance.HIGH,
    )
    alert = Alert(
        id="a1",
        user_id="user-1",
        name="N",
        conditions=[AlertCondition(AlertType.HIGH_IMPACT_EVENT, None)],
    )

    with (
        patch("scalper_today.infrastructure.database.EventRepository") as MockEventRepo,
        patch(
            "scalper_today.infrastructure.database.repositories.AlertRepository"
        ) as MockAlertRepo,
    ):
        MockEventRepo.return_value.get_events_by_date = AsyncMock(return_value=[event])
        MockAlertRepo.return_value.get_active_alerts = AsyncMock(return_value=[alert])
        MockAlertRepo.return_value.update = AsyncMock()

        await scheduler._check_and_notify()

        # Should NOT call send_event_alert again
        mock_expo.send_event_alert.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduler_ignores_far_future_events(scheduler, mock_expo, mock_db_manager):
    # Event in 15 minutes (outside 5min window)
    now_madrid = datetime.now(pytz.timezone("Europe/Madrid"))
    event_time = (now_madrid + timedelta(minutes=15)).strftime("%H:%M")
    event = EconomicEvent(
        id="event-far",
        time=event_time,
        title="T",
        country="C",
        currency="C",
        importance=Importance.HIGH,
    )
    alert = Alert(
        id="a1",
        user_id="user-1",
        name="N",
        conditions=[AlertCondition(AlertType.HIGH_IMPACT_EVENT, None)],
    )

    with (
        patch("scalper_today.infrastructure.database.EventRepository") as MockEventRepo,
        patch(
            "scalper_today.infrastructure.database.repositories.AlertRepository"
        ) as MockAlertRepo,
    ):
        MockEventRepo.return_value.get_events_by_date = AsyncMock(return_value=[event])
        MockAlertRepo.return_value.get_active_alerts = AsyncMock(return_value=[alert])
        MockAlertRepo.return_value.update = AsyncMock()

        await scheduler._check_and_notify()

        mock_expo.send_event_alert.assert_not_awaited()


def test_condition_matching_logic(scheduler):
    high_event = EconomicEvent(
        id="1",
        time="1",
        title="T",
        country="United States",
        currency="USD",
        importance=Importance.HIGH,
    )
    low_event = EconomicEvent(
        id="2",
        time="1",
        title="T",
        country="United States",
        currency="USD",
        importance=Importance.LOW,
    )

    cond_high = AlertCondition(alert_type=AlertType.HIGH_IMPACT_EVENT, value=None)
    cond_country = AlertCondition(alert_type=AlertType.SPECIFIC_COUNTRY, value="United States")

    # Test High Impact
    assert scheduler._condition_matches_event(cond_high, high_event) is True
    assert scheduler._condition_matches_event(cond_high, low_event) is False

    # Test Country Match (case insensitive)
    assert scheduler._condition_matches_event(cond_country, high_event) is True

    # Test Surprise Move (20% threshold)
    cond_surprise = AlertCondition(alert_type=AlertType.SURPRISE_MOVE, value=None)
    event_surprise = EconomicEvent(
        id="3",
        time="1",
        title="T",
        country="C",
        currency="C",
        importance=Importance.MEDIUM,
        actual="100",
        forecast="50",
    )
    event_no_surprise = EconomicEvent(
        id="4",
        time="1",
        title="T",
        country="C",
        currency="C",
        importance=Importance.MEDIUM,
        actual="100",
        forecast="95",
    )

    assert scheduler._condition_matches_event(cond_surprise, event_surprise) is True
    assert scheduler._condition_matches_event(cond_surprise, event_no_surprise) is False
