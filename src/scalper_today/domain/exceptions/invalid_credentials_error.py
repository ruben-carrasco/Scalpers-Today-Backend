from .authentication_error import AuthenticationError


class InvalidCredentialsError(AuthenticationError):
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message)
        self.code = "INVALID_CREDENTIALS"
