from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")

    model_config = {"json_schema_extra": {"example": {"detail": "Invalid email or password"}}}
