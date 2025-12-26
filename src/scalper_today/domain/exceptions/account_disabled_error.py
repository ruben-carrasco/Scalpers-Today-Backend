from .authentication_error import AuthenticationError


class AccountDisabledError(AuthenticationError):
    def __init__(self, message: str = "Account is disabled"):
        super().__init__(message=message)
        self.code = "ACCOUNT_DISABLED"
