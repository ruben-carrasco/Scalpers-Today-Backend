from pydantic import BaseModel


class MarketSentimentSchema(BaseModel):
    model_config = {"from_attributes": True}

    overall: str
    volatility: str
