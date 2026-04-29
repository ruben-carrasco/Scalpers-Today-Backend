
from pydantic import BaseModel


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, bool]
