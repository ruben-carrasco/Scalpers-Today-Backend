from dataclasses import dataclass
from typing import List
from .country_info import CountryInfo


@dataclass
class AvailableCountriesResult:
    total_countries: int
    countries: List[CountryInfo]
