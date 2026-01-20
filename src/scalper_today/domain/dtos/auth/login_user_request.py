from dataclasses import dataclass


@dataclass
class LoginUserRequest:
    email: str
    password: str
