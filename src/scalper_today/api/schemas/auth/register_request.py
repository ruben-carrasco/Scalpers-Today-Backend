from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 chars)")
    name: str = Field(..., min_length=1, max_length=100, description="User full name")
    language: str = Field(default="es", pattern="^(es|en)$", description="Preferred language")
    currency: str = Field(
        default="usd", pattern="^(usd|eur|gbp)$", description="Preferred currency"
    )
    timezone: str = Field(default="Europe/Madrid", description="Preferred timezone")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "name": "John Doe",
                "language": "es",
                "currency": "usd",
                "timezone": "Europe/Madrid",
            }
        }
    }
