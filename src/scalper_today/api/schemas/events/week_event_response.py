from datetime import datetime

from pydantic import Field

from scalper_today.domain.entities import EconomicEvent

from .event_response import EventResponse


class WeekEventResponse(EventResponse):
    event_date: str = Field(..., description="Event date in YYYY-MM-DD format")

    @classmethod
    def from_domain(cls, event: EconomicEvent) -> "WeekEventResponse":
        event_date = ""
        if isinstance(event._timestamp, datetime):
            event_date = event._timestamp.date().isoformat()

        payload = EventResponse.model_validate(event).model_dump()
        payload["event_date"] = event_date
        return cls.model_validate(payload)
