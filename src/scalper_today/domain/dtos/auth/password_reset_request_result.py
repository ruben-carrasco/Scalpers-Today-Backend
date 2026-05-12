from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordResetRequestResult:
    message: str
    reset_token: str | None = None
