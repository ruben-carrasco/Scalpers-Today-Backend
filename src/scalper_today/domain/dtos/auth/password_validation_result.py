from dataclasses import dataclass


@dataclass
class PasswordValidationResult:
    is_valid: bool
    errors: list[str]
