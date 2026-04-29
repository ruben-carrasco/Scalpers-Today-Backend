from collections.abc import Iterable
from datetime import date, datetime, time

from scalper_today.domain.entities import EconomicEvent


def sort_events(events: Iterable[EconomicEvent]) -> list[EconomicEvent]:
    return sorted(events, key=_event_sort_key)


def _event_sort_key(event: EconomicEvent) -> tuple[date, time, int, str, str]:
    event_date = event._timestamp.date() if event._timestamp else date.min
    event_time = _parse_event_time(event.time)
    return (
        event_date,
        event_time,
        -int(event.importance),
        event.country,
        event.title.lower(),
    )


def _parse_event_time(value: str) -> time:
    try:
        return datetime.strptime(value.strip()[:5], "%H:%M").time()
    except (ValueError, AttributeError):
        return time.max
