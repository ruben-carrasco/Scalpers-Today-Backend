from pydantic import BaseModel


class TodayStatsSchema(BaseModel):
    model_config = {"from_attributes": True}

    total_events: int
    high_impact: int
    medium_impact: int
    low_impact: int
