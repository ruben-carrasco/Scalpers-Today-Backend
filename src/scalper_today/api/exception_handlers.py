import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from scalper_today.domain.exceptions import (
    AuthenticationError,
    DomainException,
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidEmailError,
    PermissionDeniedError,
    ResourceNotFoundError,
    TokenExpiredError,
    TokenInvalidError,
    ValidationError,
    WeakPasswordError,
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
        if isinstance(exc, HTTPException):
            raise exc

        logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred"},
        )
