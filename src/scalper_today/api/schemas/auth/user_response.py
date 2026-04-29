from pydantic import BaseModel

from .user_preferences_response import UserPreferencesResponse


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None = None
    preferences: UserPreferencesResponse
    is_verified: bool = False

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "name": "John Doe",
                "avatar_url": None,
                "preferences": {"language": "es", "currency": "usd", "timezone": "Europe/Madrid"},
                "is_verified": False,
            }
        }
    }
