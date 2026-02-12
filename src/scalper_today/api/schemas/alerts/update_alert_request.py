from typing import Optional, List

from pydantic import BaseModel, Field

from .alert_condition_schema import AlertConditionSchema


class UpdateAlertRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    conditions: Optional[List[AlertConditionSchema]] = None
    status: Optional[str] = Field(None, pattern="^(active|paused|deleted)$")
    push_enabled: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "example": {"name": "Updated Alert Name", "status": "active", "push_enabled": True}
        }
    }
