from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordResetConfirmRequest:
    token: str
    new_password: str
