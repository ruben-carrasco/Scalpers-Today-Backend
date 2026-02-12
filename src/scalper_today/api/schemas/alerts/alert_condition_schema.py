from typing import Optional

from pydantic import BaseModel, Field


class AlertConditionSchema(BaseModel):
    alert_type: str = Field(
        ...,
        description="Type of alert trigger",
        pattern="^(high_impact_event|specific_country|specific_currency|data_release|surprise_move)$",
    )
    value: Optional[str] = Field(
        None, description="Condition value (e.g., country name, currency code)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"alert_type": "high_impact_event", "value": None},
                {"alert_type": "specific_country", "value": "United States"},
                {"alert_type": "specific_currency", "value": "USD"},
            ]
        }
    }
