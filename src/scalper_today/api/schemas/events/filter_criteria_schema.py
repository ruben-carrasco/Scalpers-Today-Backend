from typing import Optional
from pydantic import BaseModel


class FilterCriteriaSchema(BaseModel):
    model_config = {"from_attributes": True}

    importance: Optional[int] = None
    country: Optional[str] = None
    has_data: Optional[bool] = None
    search: Optional[str] = None
