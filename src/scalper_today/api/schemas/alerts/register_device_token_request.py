from typing import Optional

from pydantic import BaseModel, Field


class RegisterDeviceTokenRequest(BaseModel):
    token: str = Field(..., min_length=1, description="FCM registration token")
    device_type: str = Field(..., pattern="^(ios|android)$", description="Device platform")
    device_name: Optional[str] = Field(None, max_length=100, description="Device name/model")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "fcm_token_here_very_long_string...",
                "device_type": "android",
                "device_name": "Samsung Galaxy S21",
            }
        }
    }
