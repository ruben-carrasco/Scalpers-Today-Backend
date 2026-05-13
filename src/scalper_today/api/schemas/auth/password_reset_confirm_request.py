from pydantic import BaseModel, Field


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(
        ...,
        min_length=6,
        max_length=512,
        description="Password reset code or legacy token",
    )
    new_password: str = Field(..., min_length=8, description="New account password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "123456",
                "new_password": "NewSecurePassword123!",
            }
        }
    }
