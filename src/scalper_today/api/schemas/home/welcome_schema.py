from pydantic import BaseModel


class WelcomeSchema(BaseModel):
    model_config = {"from_attributes": True}

    greeting: str
    date: str
    time: str
