from dataclasses import dataclass, field
from typing import Any


@dataclass
class NotificationResult:
    success_count: int
    failure_count: int
    results: list[Any] = field(default_factory=list)
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None and self.success_count > 0
