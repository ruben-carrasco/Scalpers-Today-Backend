from typing import List
from .validation_error import ValidationError


class WeakPasswordError(ValidationError):
    def __init__(self, requirements: List[str] = None):
        message = "Password does not meet requirements"
        super().__init__(message=message, errors=requirements)
        self.code = "WEAK_PASSWORD"
