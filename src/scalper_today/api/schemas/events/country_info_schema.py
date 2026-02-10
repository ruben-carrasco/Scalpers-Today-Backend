from pydantic import BaseModel


class CountryInfoSchema(BaseModel):
    model_config = {"from_attributes": True}

    name: str
    event_count: int
