from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address of the account to reset")

    model_config = {"json_schema_extra": {"example": {"email": "user@example.com"}}}
