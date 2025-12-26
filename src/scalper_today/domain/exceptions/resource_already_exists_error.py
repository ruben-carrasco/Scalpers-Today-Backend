from .base import DomainException


class ResourceAlreadyExistsError(DomainException):
    def __init__(self, resource_type: str, identifier: str = ""):
        message = f"{resource_type} already exists"
        if identifier:
            message = f"{resource_type} already exists: {identifier}"
        super().__init__(message=message, code="ALREADY_EXISTS")
