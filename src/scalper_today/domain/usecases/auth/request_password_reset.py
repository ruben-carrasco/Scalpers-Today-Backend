import logging

from scalper_today.domain.dtos import PasswordResetRequest, PasswordResetRequestResult
from scalper_today.domain.interfaces import IAuthService, IUserRepository

logger = logging.getLogger(__name__)

PASSWORD_RESET_MESSAGE = (
    "If an account exists for that email, password reset instructions have been generated."
)


class RequestPasswordResetUseCase:
    def __init__(self, user_repository: IUserRepository, auth_service: IAuthService):
        self.user_repository = user_repository
        self.auth_service = auth_service

    async def execute(self, request: PasswordResetRequest) -> PasswordResetRequestResult:
        email = request.email.lower().strip()
        user = await self.user_repository.get_by_email(email)

        if not user or not user.is_active:
            logger.info("Password reset requested for unknown or inactive account")
            return PasswordResetRequestResult(message=PASSWORD_RESET_MESSAGE)

        reset_token = self.auth_service.create_password_reset_token(user)
        logger.info(f"Password reset requested for user: {user.email}")
        return PasswordResetRequestResult(message=PASSWORD_RESET_MESSAGE, reset_token=reset_token)
