from pydantic import BaseModel, Field


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=20, description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New account password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "new_password": "NewSecurePassword123!",
            }
        }
    }
