from dataclasses import dataclass
from typing import Optional


@dataclass
class AIAnalysis:
    summary: str = "Analysis pending..."
    impact: str = "N/A"
    sentiment: str = "NEUTRAL"
    macro_context: Optional[str] = None
    technical_levels: Optional[str] = None
    trading_strategies: Optional[str] = None
    impacted_assets: Optional[str] = None
    is_deep_analysis: bool = False

    @classmethod
    def pending(cls) -> "AIAnalysis":
        return cls()
