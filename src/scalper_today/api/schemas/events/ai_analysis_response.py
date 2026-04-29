
from pydantic import BaseModel, Field


class AIAnalysisResponse(BaseModel):
    model_config = {"from_attributes": True}

    summary: str = Field(..., description="Summary of the AI analysis")
    impact: str = Field(..., description="Calculated impact (HIGH, MEDIUM, LOW, N/A)")
    sentiment: str = Field(..., description="Market sentiment (BULLISH, BEARISH, NEUTRAL)")
    macro_context: str | None = Field(None, description="Macroeconomic context")
    technical_levels: str | None = Field(None, description="Key technical levels")
    trading_strategies: str | None = Field(None, description="Recommended trading strategies")
    impacted_assets: str | list[str] | None = Field(
        None, description="Assets likely to be impacted"
    )
