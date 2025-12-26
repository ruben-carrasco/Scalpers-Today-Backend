from .base import DomainException


class PermissionDeniedError(DomainException):
    def __init__(self, message: str = "Permission denied", action: str = ""):
        details = {"action": action} if action else None
        super().__init__(message=message, code="PERMISSION_DENIED", details=details)
