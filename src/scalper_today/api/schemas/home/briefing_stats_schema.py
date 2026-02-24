from pydantic import BaseModel


class BriefingStatsSchema(BaseModel):
    model_config = {"from_attributes": True}

    sentiment: str
    volatility_level: str
    total_events_today: int
    high_impact_count: int
