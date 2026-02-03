from dataclasses import dataclass, field
from typing import List, Any, Optional


@dataclass
class NotificationResult:
    success_count: int
    failure_count: int
    results: List[Any] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.error is None and self.success_count > 0
