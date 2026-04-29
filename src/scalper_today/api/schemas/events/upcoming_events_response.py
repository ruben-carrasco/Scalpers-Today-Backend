
from pydantic import BaseModel

from .event_response import EventResponse


class UpcomingEventsResponse(BaseModel):
    model_config = {"from_attributes": True}

    current_time: str
    count: int
    events: list[EventResponse]
