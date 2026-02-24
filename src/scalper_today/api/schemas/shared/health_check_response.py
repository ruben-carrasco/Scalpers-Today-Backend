from pydantic import BaseModel
from .health_checks_schema import HealthChecksSchema


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    environment: str
    checks: HealthChecksSchema
