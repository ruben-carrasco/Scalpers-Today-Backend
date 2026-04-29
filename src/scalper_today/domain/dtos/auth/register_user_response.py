from dataclasses import dataclass

from scalper_today.domain.entities import AuthToken, User


@dataclass
class RegisterUserResponse:
    user: User
    token: AuthToken
