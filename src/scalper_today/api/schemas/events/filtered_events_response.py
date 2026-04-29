from pydantic import BaseModel

from .event_response import EventResponse
from .filter_criteria_schema import FilterCriteriaSchema


class FilteredEventsResponse(BaseModel):
    model_config = {"from_attributes": True}

    total: int
    filters_applied: FilterCriteriaSchema
    events: list[EventResponse]
