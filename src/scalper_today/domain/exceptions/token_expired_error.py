from .authentication_error import AuthenticationError


class TokenExpiredError(AuthenticationError):
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message)
        self.code = "TOKEN_EXPIRED"
