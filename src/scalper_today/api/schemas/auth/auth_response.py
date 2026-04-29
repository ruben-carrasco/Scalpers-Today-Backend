from pydantic import BaseModel

from .token_response import TokenResponse
from .user_response import UserResponse


class AuthResponse(BaseModel):
    user: UserResponse
    token: TokenResponse

    model_config = {
        "json_schema_extra": {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "name": "John Doe",
                    "avatar_url": None,
                    "preferences": {
                        "language": "es",
                        "currency": "usd",
                        "timezone": "Europe/Madrid",
                    },
                    "is_verified": False,
                },
                "token": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 2592000,
                },
            }
        }
    }
