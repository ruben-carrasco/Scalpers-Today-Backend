from typing import List
from .base import DomainException


class ValidationError(DomainException):
    def __init__(self, message: str = "Validation failed", errors: List[str] = None):
        details = {"errors": errors} if errors else None
        super().__init__(message=message, code="VALIDATION_ERROR", details=details)
        self.errors = errors or []
