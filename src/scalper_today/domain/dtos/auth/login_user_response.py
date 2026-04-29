from dataclasses import dataclass

from scalper_today.domain.entities import AuthToken, User


@dataclass
class LoginUserResponse:
    user: User
    token: AuthToken
