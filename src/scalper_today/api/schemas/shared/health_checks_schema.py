from pydantic import BaseModel


class HealthChecksSchema(BaseModel):
    database: str
    ai_service: str
