from pydantic import BaseModel, Field


class BackfillAnalysisResponse(BaseModel):
    status: str = Field(description="Operation status.")
    message: str = Field(description="Human-readable operation summary.")
    total_events: int = Field(description="Total stored events found in the requested range.")
    quick_requested: int = Field(description="Events that were missing quick AI analysis.")
    quick_saved: int = Field(description="Events updated with quick AI analysis.")
    deep_requested: int = Field(description="High-impact events missing deep AI analysis.")
    deep_saved: int = Field(description="High-impact events updated with deep AI analysis.")
