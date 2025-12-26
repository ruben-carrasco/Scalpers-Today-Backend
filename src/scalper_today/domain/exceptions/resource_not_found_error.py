from .base import DomainException


class ResourceNotFoundError(DomainException):
    def __init__(self, resource_type: str, resource_id: str = ""):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} not found: {resource_id}"
        details = {"resource_type": resource_type}
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message=message, code="NOT_FOUND", details=details)
