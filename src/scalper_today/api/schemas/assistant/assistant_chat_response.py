from pydantic import BaseModel, Field


class AssistantChatResponse(BaseModel):
    answer: str = Field(..., description="Educational assistant answer")
    disclaimer: str = Field(
        "Contenido educativo. No constituye asesoramiento financiero.",
        description="Financial safety disclaimer",
    )
