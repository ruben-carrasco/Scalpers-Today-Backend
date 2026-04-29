
from pydantic import BaseModel

from .alert_condition_schema import AlertConditionSchema


class AlertResponse(BaseModel):
    id: str
    name: str
    description: str | None
    conditions: list[AlertConditionSchema]
    status: str
    push_enabled: bool
    trigger_count: int
    last_triggered_at: str | None
    created_at: str
    updated_at: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "US High Impact Events",
                "description": "Alert me for all high-impact US economic events",
                "conditions": [
                    {"alert_type": "high_impact_event", "value": None},
                    {"alert_type": "specific_country", "value": "United States"},
                ],
                "status": "active",
                "push_enabled": True,
                "trigger_count": 5,
                "last_triggered_at": "2026-01-12T10:30:00",
                "created_at": "2026-01-10T08:00:00",
                "updated_at": "2026-01-12T10:30:00",
            }
        }
    }
