from dataclasses import dataclass

from .country_info import CountryInfo


@dataclass
class AvailableCountriesResult:
    total_countries: int
    countries: list[CountryInfo]
