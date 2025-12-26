from .base import DomainException


class ExternalServiceError(DomainException):
    def __init__(self, service: str, message: str = "External service error"):
        details = {"service": service}
        super().__init__(message=message, code="EXTERNAL_SERVICE_ERROR", details=details)
        self.service = service
