from .validation_error import ValidationError


class InvalidEmailError(ValidationError):
    def __init__(self, email: str = ""):
        message = f"Invalid email format: {email}" if email else "Invalid email format"
        super().__init__(message=message)
        self.code = "INVALID_EMAIL"
