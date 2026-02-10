from typing import Optional
from pydantic import BaseModel, Field
from .ai_analysis_response import AIAnalysisResponse


class EventResponse(BaseModel):
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "event_123",
                "time": "14:30",
                "title": "Non-Farm Payrolls",
                "country": "United States",
                "currency": "USD",
                "importance": 3,
                "actual": "225K",
                "forecast": "180K",
                "previous": "150K",
                "surprise": "positive",
                "ai_analysis": {
                    "summary": "Strong job growth exceeds expectations, potentially delaying rate cuts.",
                    "impact": "HIGH",
                    "sentiment": "BULLISH",
                },
            }
        },
    }

    id: str = Field(..., description="Unique event identifier")
    time: str = Field(..., description="Event time (local)")
    title: str = Field(..., description="Event title")
    url: str = Field("", description="URL for more information")
    country: str = Field(..., description="Country code or name")
    currency: str = Field(..., description="Currency affected")
    importance: int = Field(..., ge=1, le=3, description="Event importance (1-3 stars)")
    actual: str = Field("", description="Actual value released")
    forecast: str = Field("", description="Forecast value")
    previous: str = Field("", description="Previous value")
    surprise: str = Field("neutral", description="Surprise type (positive, negative, neutral)")
    ai_analysis: Optional[AIAnalysisResponse] = Field(None, description="AI-generated analysis")
