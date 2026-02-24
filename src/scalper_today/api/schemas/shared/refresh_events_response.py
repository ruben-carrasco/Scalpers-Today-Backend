from pydantic import BaseModel


class RefreshEventsResponse(BaseModel):
    status: str
    message: str
    count: int
