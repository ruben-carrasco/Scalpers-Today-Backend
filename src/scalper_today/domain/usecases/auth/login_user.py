import logging

from scalper_today.domain.dtos import LoginUserRequest, LoginUserResponse
from scalper_today.domain.interfaces import IUserRepository, IAuthService
from scalper_today.domain.exceptions import (
    InvalidCredentialsError,
    AccountDisabledError,
)

logger = logging.getLogger(__name__)


class LoginUserUseCase:
    def __init__(self, user_repository: IUserRepository, auth_service: IAuthService):
        self.user_repository = user_repository
        self.auth_service = auth_service

    async def execute(self, request: LoginUserRequest) -> LoginUserResponse:
        email = request.email.lower().strip()
        user = await self.user_repository.get_by_email(email)
        password_valid = False
        token = None

        if not user:
            logger.warning(f"Login attempt with non-existent email: {request.email}")
            raise InvalidCredentialsError()

        password_valid = await self.auth_service.verify_password(
            request.password, user.hashed_password
        )
        if not password_valid:
            logger.warning(f"Failed login attempt for user: {user.email}")
            raise InvalidCredentialsError()

        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {user.email}")
            raise AccountDisabledError()

        token = self.auth_service.create_access_token(user)

        logger.info(f"User logged in successfully: {user.email}")

        response = LoginUserResponse(user=user, token=token)
        return response
