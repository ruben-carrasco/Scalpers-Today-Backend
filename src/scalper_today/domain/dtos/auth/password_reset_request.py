from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordResetRequest:
    email: str
