from .base import DomainException


class AuthenticationError(DomainException):
    def __init__(self, message: str = "Authentication failed", details: dict = None):
        super().__init__(message=message, code="AUTH_ERROR", details=details)
