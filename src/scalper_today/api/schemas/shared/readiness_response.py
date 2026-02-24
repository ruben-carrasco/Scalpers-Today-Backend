from typing import Dict
from pydantic import BaseModel


class ReadinessResponse(BaseModel):
    status: str
    checks: Dict[str, bool]
