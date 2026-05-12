from pydantic import BaseModel, Field


class PasswordResetResponse(BaseModel):
    message: str = Field(..., description="Generic password reset status message")
    reset_token: str | None = Field(
        default=None,
        description="Development/test token. Production integrations should send it by email.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": (
                    "If an account exists for that email, password reset instructions have "
                    "been generated."
                )
            }
        }
    }
