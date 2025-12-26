from .authentication_error import AuthenticationError


class TokenInvalidError(AuthenticationError):
    def __init__(self, message: str = "Token is invalid"):
        super().__init__(message=message)
        self.code = "TOKEN_INVALID"
