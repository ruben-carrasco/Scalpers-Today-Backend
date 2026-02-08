from pydantic import BaseModel


class UserPreferencesResponse(BaseModel):
    language: str
    currency: str
    timezone: str
