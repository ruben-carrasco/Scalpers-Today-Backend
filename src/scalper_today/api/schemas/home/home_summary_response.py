from typing import List, Optional
from pydantic import BaseModel
from ..events.event_response import EventResponse
from .welcome_schema import WelcomeSchema
from .today_stats_schema import TodayStatsSchema
from .market_sentiment_schema import MarketSentimentSchema


class HomeSummaryResponse(BaseModel):
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "welcome": {
                    "greeting": "Buenos días",
                    "date": "Lunes, 09 de Marzo 2026",
                    "time": "09:00",
                },
                "today_stats": {
                    "total_events": 45,
                    "high_impact": 2,
                    "medium_impact": 12,
                    "low_impact": 31,
                },
                "next_event": {
                    "id": "e1",
                    "time": "14:30",
                    "title": "CPI Data",
                    "country": "USA",
                    "importance": 3,
                },
                "market_sentiment": {"overall": "BULLISH", "volatility": "MEDIUM"},
                "highlights": [],
            }
        },
    }

    welcome: WelcomeSchema
    today_stats: TodayStatsSchema
    next_event: Optional[EventResponse]
    market_sentiment: MarketSentimentSchema
    highlights: List[EventResponse]
