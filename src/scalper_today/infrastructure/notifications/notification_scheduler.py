import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Set, List, Optional

import pytz
from sqlalchemy.ext.asyncio import AsyncSession

from scalper_today.domain.entities import Alert, AlertCondition, EconomicEvent, AlertType
from .expo_push_service import ExpoPushService

logger = logging.getLogger(__name__)


class NotificationScheduler:
    TZ_MADRID = pytz.timezone("Europe/Madrid")

    def __init__(
        self,
        expo_push_service: ExpoPushService,
        database_manager,  # DatabaseManager
        check_interval_seconds: int = 60,  # Check every minute
        notify_before_minutes: int = 5,  # Notify X minutes before event
    ):
        self.expo_push_service = expo_push_service
        self.database_manager = database_manager
        self.check_interval = check_interval_seconds
        self.notify_before = timedelta(minutes=notify_before_minutes)

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._notified_events: Dict[str, Set[str]] = {}  # event_id -> set of notified user_ids
        self._last_check_date: Optional[object] = None  # date of last check, for daily cache reset

    async def start(self):
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"📅 Notification scheduler started (check every {self.check_interval}s, notify {self.notify_before.seconds // 60}min before)"
        )

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("📅 Notification scheduler stopped")

    async def _run_loop(self):
        while self._running:
            try:
                await self._check_and_notify()
            except Exception as e:
                logger.error(f"Error in notification scheduler: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

    async def _check_and_notify(self):
        self._cleanup_notified_cache()
        now = datetime.now(timezone.utc)
        # Ventana: 5 minutos antes del evento hasta 1 minuto después
        notify_window_start = now
        notify_window_end = now + self.notify_before + timedelta(minutes=1)

        logger.info(f"🔔 [SCHEDULER] Check at {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(
            f"🔔 [SCHEDULER] Window: {notify_window_start.strftime('%H:%M')} to {notify_window_end.strftime('%H:%M')} UTC"
        )

        async with self.database_manager.session() as session:
            # Get today's events
            from scalper_today.infrastructure.database import EventRepository

            event_repo = EventRepository(session)

            # Use Madrid date since event times are stored in Madrid timezone
            madrid_today = datetime.now(self.TZ_MADRID).date()
            events = await event_repo.get_events_by_date(madrid_today)

            if not events:
                logger.info("📭 [SCHEDULER] No events found for today")
                return

            logger.info(f"📋 [SCHEDULER] Found {len(events)} total events for today")

            # Get all active alerts first to log them
            from scalper_today.infrastructure.database.alert_repository import AlertRepository

            alert_repo = AlertRepository(session)
            all_alerts = await alert_repo.get_active_alerts()
            logger.info(f"🔔 [SCHEDULER] Found {len(all_alerts)} active alerts with push enabled")
            for alert in all_alerts:
                conditions_str = ", ".join(
                    [f"{c.alert_type.value}={c.value}" for c in alert.conditions]
                )
                logger.info(
                    f"   📌 Alert '{alert.name}' (user={alert.user_id[:8]}...): [{conditions_str}]"
                )

            # Filter events in notification window
            upcoming_events = []
            for event in events:
                # Parse event time string (format: "HH:MM") to datetime
                event_time = self._parse_event_time(event.time, madrid_today)
                if event_time:
                    time_diff_min = (event_time - now).total_seconds() / 60
                    # Check if event is in our notification window
                    if notify_window_start <= event_time <= notify_window_end:
                        upcoming_events.append(event)
                        logger.info(
                            f"✅ [SCHEDULER] IN WINDOW: '{event.title}' ({event.country}) at {event.time} Madrid (in {time_diff_min:.0f} min)"
                        )
                    elif -30 <= time_diff_min <= 30:
                        # Log nearby events for debugging
                        logger.info(
                            f"⏭️ [SCHEDULER] OUTSIDE: '{event.title}' ({event.country}) at {event.time} Madrid (diff: {time_diff_min:.0f} min)"
                        )

            if not upcoming_events:
                logger.info("📭 [SCHEDULER] No events in notification window")
                return

            logger.info(
                f"🎯 [SCHEDULER] Processing {len(upcoming_events)} events against {len(all_alerts)} alerts"
            )

            if not all_alerts:
                logger.info("📭 [SCHEDULER] No active alerts found")
                return

            # Match events to alerts
            for event in upcoming_events:
                await self._process_event_notifications(session, event, all_alerts)

    async def _process_event_notifications(
        self, session: AsyncSession, event: EconomicEvent, alerts: List[Alert]
    ):
        event_id = event.id or f"{event.country}_{event.title}_{event.time}"

        logger.info(
            f"🔍 [SCHEDULER] Processing event: '{event.title}' | country={event.country} | currency={event.currency} | importance={event.importance}"
        )

        # Track users to notify for this event
        users_to_notify: Set[str] = set()

        for alert in alerts:
            user_id = alert.user_id

            # Skip if already notified this user for this event
            if event_id in self._notified_events:
                if user_id in self._notified_events[event_id]:
                    logger.debug(f"   ⏭️ Already notified user {user_id[:8]}... for this event")
                    continue

            # Check if alert conditions match this event
            matches = self._alert_matches_event(alert, event)
            conditions_str = ", ".join(
                [f"{c.alert_type.value}={c.value}" for c in alert.conditions]
            )
            if matches:
                logger.info(f"   ✅ MATCH: Alert '{alert.name}' [{conditions_str}] matches event!")
                users_to_notify.add(user_id)
            else:
                logger.debug(f"   ❌ NO MATCH: Alert '{alert.name}' [{conditions_str}]")

        if not users_to_notify:
            logger.info("   📭 No users to notify for this event")
            return

        logger.info(f"🎯 [SCHEDULER] Event '{event.title}' matches {len(users_to_notify)} users")

        # Get device tokens for all users
        from scalper_today.infrastructure.database.device_token_repository import (
            DeviceTokenRepository,
        )

        device_repo = DeviceTokenRepository(session)

        all_tokens = []
        for user_id in users_to_notify:
            tokens = await device_repo.get_by_user_id(user_id, active_only=True)
            all_tokens.extend([t.token for t in tokens])

        if not all_tokens:
            logger.warning(f"No device tokens found for {len(users_to_notify)} users")
            return

        # Send notification with retry
        result = None
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            result = await self.expo_push_service.send_event_alert(
                tokens=all_tokens,
                event_name=event.title,
                importance=event.importance,
                country=event.country,
                currency=event.currency,
                scheduled_time=event.time,
            )
            if result.success_count > 0 or attempt == max_retries:
                break
            logger.warning(
                f"Notification send failed (attempt {attempt}/{max_retries}), retrying..."
            )
            await asyncio.sleep(1)

        logger.info(
            f"Sent notifications for '{event.title}': "
            f"{result.success_count} success, {result.failure_count} failures"
        )

        # Mark as notified
        if event_id not in self._notified_events:
            self._notified_events[event_id] = set()
        self._notified_events[event_id].update(users_to_notify)

        # Update alert trigger counts
        from scalper_today.infrastructure.database.alert_repository import AlertRepository

        alert_repo = AlertRepository(session)

        for alert in alerts:
            if alert.user_id in users_to_notify and self._alert_matches_event(alert, event):
                alert.trigger_count += 1
                alert.last_triggered_at = datetime.now(timezone.utc)
                await alert_repo.update(alert)

        # Clean up old notified events (older than 1 day)
        self._cleanup_notified_cache()

    def _alert_matches_event(self, alert: Alert, event: EconomicEvent) -> bool:
        for condition in alert.conditions:
            if self._condition_matches_event(condition, event):
                return True
        return False

    def _condition_matches_event(self, condition: AlertCondition, event: EconomicEvent) -> bool:
        alert_type = condition.alert_type
        value = condition.value

        if alert_type == AlertType.HIGH_IMPACT_EVENT:
            # High impact = importance 3
            match = event.importance >= 3
            logger.debug(f"      HIGH_IMPACT: importance={event.importance} >= 3? {match}")
            return match

        elif alert_type == AlertType.SPECIFIC_COUNTRY:
            # Match country name (case insensitive)
            if value and event.country:
                match = value.lower() == event.country.lower()
                logger.debug(f"      SPECIFIC_COUNTRY: '{value}' == '{event.country}'? {match}")
                return match
            logger.debug(
                f"      SPECIFIC_COUNTRY: value={value}, event.country={event.country} - False"
            )
            return False

        elif alert_type == AlertType.SPECIFIC_CURRENCY:
            # Match currency code
            if value and event.currency:
                match = value.upper() == event.currency.upper()
                logger.debug(f"      SPECIFIC_CURRENCY: '{value}' == '{event.currency}'? {match}")
                return match
            logger.debug(
                f"      SPECIFIC_CURRENCY: value={value}, event.currency={event.currency} - False"
            )
            return False

        elif alert_type == AlertType.DATA_RELEASE:
            # Any event with actual data released
            match = event.actual is not None and event.actual != ""
            logger.debug(f"      DATA_RELEASE: actual='{event.actual}' - {match}")
            return match

        elif alert_type == AlertType.SURPRISE_MOVE:
            # When actual differs significantly from forecast
            # This would need more complex logic with numeric parsing
            if event.actual and event.forecast:
                try:
                    actual_val = self._parse_numeric(event.actual)
                    forecast_val = self._parse_numeric(event.forecast)
                    if actual_val is not None and forecast_val is not None:
                        # More than 20% difference
                        if forecast_val != 0:
                            diff_pct = abs(actual_val - forecast_val) / abs(forecast_val)
                            return diff_pct > 0.2
                except Exception:
                    pass
            return False

        return False

    def _parse_numeric(self, value: str) -> Optional[float]:
        if not value:
            return None

        # Remove common suffixes and clean up
        cleaned = value.strip().replace("%", "").replace("K", "000").replace("M", "000000")
        cleaned = cleaned.replace(",", ".")

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_event_time(self, time_str: str, event_date) -> Optional[datetime]:
        if not time_str:
            return None

        try:
            parts = time_str.strip().split(":")
            if len(parts) >= 2:
                hour = int(parts[0])
                minute = int(parts[1])
                naive_dt = datetime(
                    year=event_date.year,
                    month=event_date.month,
                    day=event_date.day,
                    hour=hour,
                    minute=minute,
                )
                madrid_dt = self.TZ_MADRID.localize(naive_dt)
                return madrid_dt.astimezone(pytz.utc)
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse event time '{time_str}': {e}")

        return None

    def _cleanup_notified_cache(self):
        today = datetime.now(self.TZ_MADRID).date()
        if self._last_check_date and self._last_check_date != today:
            self._notified_events.clear()
            logger.info("🧹 [SCHEDULER] Cleared notification cache for new day")
        self._last_check_date = today
