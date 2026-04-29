from pydantic import BaseModel


class FilterCriteriaSchema(BaseModel):
    model_config = {"from_attributes": True}

    importance: int | None = None
    country: str | None = None
    has_data: bool | None = None
    search: str | None = None
