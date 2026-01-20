from dataclasses import dataclass

from scalper_today.domain.entities import User, AuthToken


@dataclass
class LoginUserResponse:
    user: User
    token: AuthToken
