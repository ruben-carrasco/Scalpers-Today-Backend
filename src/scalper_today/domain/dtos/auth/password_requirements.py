from dataclasses import dataclass


@dataclass
class PasswordRequirements:
    min_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = False
