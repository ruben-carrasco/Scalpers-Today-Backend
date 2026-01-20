import re
from scalper_today.domain.dtos import PasswordRequirements, PasswordValidationResult


class PasswordValidator:
    SPECIAL_CHARS_PATTERN = r'[!@#$%^&*(),.?":{}|<>]'

    def __init__(self, requirements: PasswordRequirements = None):
        self.requirements = requirements or PasswordRequirements()

    def validate(self, password: str) -> PasswordValidationResult:
        errors = []

        if len(password) < self.requirements.min_length:
            errors.append(f"Password must be at least {self.requirements.min_length} characters")

        if self.requirements.require_uppercase and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if self.requirements.require_lowercase and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if self.requirements.require_digit and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if self.requirements.require_special and not re.search(
            self.SPECIAL_CHARS_PATTERN, password
        ):
            errors.append("Password must contain at least one special character")

        is_valid = len(errors) == 0
        result = PasswordValidationResult(is_valid=is_valid, errors=errors)

        return result

    def is_valid(self, password: str) -> bool:
        result = self.validate(password)

        return result.is_valid
