from typing import List
from pydantic import BaseModel
from .country_info_schema import CountryInfoSchema


class AvailableCountriesResponse(BaseModel):
    model_config = {"from_attributes": True}

    total_countries: int
    countries: List[CountryInfoSchema]
