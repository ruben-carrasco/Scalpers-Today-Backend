from .external_service_error import ExternalServiceError


class DatabaseError(ExternalServiceError):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(service="database", message=message)
        self.code = "DATABASE_ERROR"
