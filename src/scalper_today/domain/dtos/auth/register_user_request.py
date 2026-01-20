from dataclasses import dataclass


@dataclass
class RegisterUserRequest:
    email: str
    password: str
    name: str
    language: str = "es"
    currency: str = "usd"
    timezone: str = "Europe/Madrid"
