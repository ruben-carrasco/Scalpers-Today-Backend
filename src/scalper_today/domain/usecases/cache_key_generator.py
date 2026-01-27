import hashlib
from datetime import datetime
from typing import List

from scalper_today.domain.entities import EconomicEvent


class CacheKeyGenerator:
    @staticmethod
    def for_event(event: EconomicEvent) -> str:
        return hashlib.md5(event.cache_signature.encode("utf-8")).hexdigest()

    @staticmethod
    def for_daily_briefing(events: List[EconomicEvent], date: datetime) -> str:
        date_str = date.strftime("%Y-%m-%d")

        if not events:
            return f"DAILY_BRIEF_{date_str}_empty"

        critical = [e for e in events if e.is_high_impact]

        if critical:
            data = "".join(f"{e.id}-{e.actual}" for e in critical)
        else:
            data = "".join(f"{e.time}-{e.title[:15]}" for e in events[:10])

        content_hash = hashlib.md5(data.encode("utf-8")).hexdigest()[:12]
        return f"DAILY_BRIEF_{date_str}_{content_hash}"
