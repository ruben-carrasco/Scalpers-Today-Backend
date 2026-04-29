
from scalper_today.domain.dtos import EventFilterCriteria
from scalper_today.domain.entities import EconomicEvent


class EventFilter:
    @staticmethod
    def apply_criteria(
        events: list[EconomicEvent], criteria: EventFilterCriteria
    ) -> list[EconomicEvent]:
        filtered = events

        if criteria.importance is not None:
            filtered = [e for e in filtered if int(e.importance) == criteria.importance]

        if criteria.country:
            country_lower = criteria.country.lower()
            filtered = [e for e in filtered if country_lower in e.country.lower()]

        if criteria.has_data is True:
            filtered = [e for e in filtered if e.has_data]

        if criteria.search:
            search_lower = criteria.search.lower()
            filtered = [
                e
                for e in filtered
                if search_lower in e.title.lower()
                or search_lower in e.country.lower()
                or search_lower in e.currency.lower()
            ]

        return filtered

    @staticmethod
    def by_importance(events: list[EconomicEvent], importance: int) -> list[EconomicEvent]:
        return [e for e in events if int(e.importance) == importance]

    @staticmethod
    def high_impact_only(events: list[EconomicEvent]) -> list[EconomicEvent]:
        return [e for e in events if e.is_high_impact]

    @staticmethod
    def without_analysis(events: list[EconomicEvent]) -> list[EconomicEvent]:
        return [e for e in events if e.ai_analysis is None]

    @staticmethod
    def with_data(events: list[EconomicEvent]) -> list[EconomicEvent]:
        return [e for e in events if e.has_data]
