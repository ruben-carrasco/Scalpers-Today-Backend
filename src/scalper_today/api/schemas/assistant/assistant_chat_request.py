from pydantic import BaseModel, Field


class AssistantChatContext(BaseModel):
    screen: str | None = Field(None, max_length=80, description="Current app screen")
    event_title: str | None = Field(None, max_length=160, description="Selected event title")
    country: str | None = Field(None, max_length=80, description="Event country")
    currency: str | None = Field(None, max_length=16, description="Event currency")
    importance: int | None = Field(None, ge=1, le=3, description="Event importance from 1 to 3")
    actual: str | None = Field(None, max_length=80, description="Actual released value")
    forecast: str | None = Field(None, max_length=80, description="Market forecast")
    previous: str | None = Field(None, max_length=80, description="Previous value")
    ai_summary: str | None = Field(None, max_length=800, description="Existing AI event summary")


class AssistantChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=600,
        description="User question about macro concepts, events, or app analysis",
    )
    context: AssistantChatContext | None = Field(
        None,
        description="Optional context from the current app screen or selected event",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "¿Por qué el IPC afecta al dólar?",
                "context": {
                    "screen": "event_detail",
                    "event_title": "Core CPI",
                    "country": "US",
                    "currency": "USD",
                    "importance": 3,
                    "forecast": "0.3%",
                    "previous": "0.2%",
                },
            }
        }
    }
