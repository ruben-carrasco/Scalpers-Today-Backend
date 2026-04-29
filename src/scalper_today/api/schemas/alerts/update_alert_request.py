from pydantic import BaseModel, Field

from .alert_condition_schema import AlertConditionSchema


class UpdateAlertRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    conditions: list[AlertConditionSchema] | None = None
    status: str | None = Field(None, pattern="^(active|paused|deleted)$")
    push_enabled: bool | None = None

    model_config = {
        "json_schema_extra": {
            "example": {"name": "Updated Alert Name", "status": "active", "push_enabled": True}
        }
    }
