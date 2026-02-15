import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from scalper_today.domain.exceptions import (
    DomainException,
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    ValidationError,
    InvalidEmailError,
    WeakPasswordError,
    DuplicateEmailError,
    ResourceNotFoundError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        status_code = status.HTTP_400_BAD_REQUEST

        if isinstance(
            exc,
            (AuthenticationError, InvalidCredentialsError, TokenExpiredError, TokenInvalidError),
        ):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, PermissionDeniedError):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, ResourceNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, DuplicateEmailError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(exc, (ValidationError, InvalidEmailError, WeakPasswordError)):
            status_code = status.HTTP_400_BAD_REQUEST

        logger.warning(f"Domain exception caught: {exc.code} - {exc.message}")

        return JSONResponse(status_code=status_code, content={"detail": exc.to_dict()})

    @app.exception_handler(Exception)
    async def universal_exception_handler(request: Request, exc: Exception):
        # Don't catch FastAPI's own HTTPExceptions here, they have their own handler
        if hasattr(exc, "status_code"):
            raise exc

        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred"},
        )
