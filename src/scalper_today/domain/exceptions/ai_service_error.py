from .external_service_error import ExternalServiceError


class AIServiceError(ExternalServiceError):
    def __init__(self, message: str = "AI service unavailable"):
        super().__init__(service="ai", message=message)
        self.code = "AI_SERVICE_ERROR"
