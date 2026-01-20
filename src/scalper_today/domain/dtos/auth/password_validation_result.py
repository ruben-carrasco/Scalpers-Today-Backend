from dataclasses import dataclass
from typing import List


@dataclass
class PasswordValidationResult:
    is_valid: bool
    errors: List[str]
