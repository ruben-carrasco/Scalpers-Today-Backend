from .validation_error import ValidationError


class DuplicateEmailError(ValidationError):
    def __init__(self, email: str = ""):
        message = "Email already registered"
        super().__init__(message=message)
        self.code = "DUPLICATE_EMAIL"
