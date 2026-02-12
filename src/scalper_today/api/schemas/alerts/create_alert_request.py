from typing import Optional, List

from pydantic import BaseModel, Field

from .alert_condition_schema import AlertConditionSchema


class CreateAlertRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Alert name")
    description: Optional[str] = Field(None, description="Alert description")
    conditions: List[AlertConditionSchema] = Field(
        ..., min_length=1, description="Alert conditions"
    )
    push_enabled: bool = Field(default=True, description="Enable push notifications")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "US High Impact Events",
                "description": "Alert me for all high-impact US economic events",
                "conditions": [
                    {"alert_type": "high_impact_event", "value": None},
                    {"alert_type": "specific_country", "value": "United States"},
                ],
                "push_enabled": True,
            }
        }
    }
