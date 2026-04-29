from pydantic import BaseModel

from .event_response import EventResponse


class ImportanceEventsResponse(BaseModel):
    model_config = {"from_attributes": True}

    importance: int
    count: int
    events: list[EventResponse]
