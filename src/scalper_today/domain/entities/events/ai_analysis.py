from dataclasses import dataclass


@dataclass
class AIAnalysis:
    summary: str = "Analysis pending..."
    impact: str = "N/A"
    sentiment: str = "NEUTRAL"
    macro_context: str | None = None
    technical_levels: str | None = None
    trading_strategies: str | None = None
    impacted_assets: str | list[str] | None = None
    is_deep_analysis: bool = False

    @classmethod
    def pending(cls) -> "AIAnalysis":
        return cls()
