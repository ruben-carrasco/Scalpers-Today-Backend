from dataclasses import dataclass


@dataclass
class AuthToken:
    access_token: str
    token_type: str
    expires_in: int
