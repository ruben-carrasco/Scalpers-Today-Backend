
from scalper_today.domain.dtos import AvailableCountriesResult, CountryInfo
from scalper_today.domain.entities import EconomicEvent


class GetAvailableCountriesUseCase:
    def execute(self, events: list[EconomicEvent]) -> AvailableCountriesResult:
        country_counts = {}
        for event in events:
            country = event.country
            if country in country_counts:
                country_counts[country] += 1
            else:
                country_counts[country] = 1

        sorted_countries = sorted(country_counts.keys())

        countries = []
        for country in sorted_countries:
            info = CountryInfo(
                name=country,
                event_count=country_counts[country],
            )
            countries.append(info)

        result = AvailableCountriesResult(
            total_countries=len(countries),
            countries=countries,
        )

        return result
