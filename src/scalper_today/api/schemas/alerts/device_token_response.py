from typing import Optional

from pydantic import BaseModel


class DeviceTokenResponse(BaseModel):
    id: str
    device_type: str
    device_name: Optional[str]
    is_active: bool
    created_at: str
    last_used_at: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "device_type": "android",
                "device_name": "Samsung Galaxy S21",
                "is_active": True,
                "created_at": "2026-01-10T08:00:00",
                "last_used_at": "2026-01-12T10:00:00",
            }
        }
    }
