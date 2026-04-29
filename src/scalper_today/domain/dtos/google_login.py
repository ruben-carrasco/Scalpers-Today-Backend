from dataclasses import dataclass


@dataclass
class GoogleLoginRequest:
    id_token: str
