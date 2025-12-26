from typing import Dict, Any, Optional


class DomainException(Exception):
    def __init__(
        self, message: str, code: str = "DOMAIN_ERROR", details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "error": self.code,
            "message": self.message,
        }

        if self.details:
            result["details"] = self.details

        return result
