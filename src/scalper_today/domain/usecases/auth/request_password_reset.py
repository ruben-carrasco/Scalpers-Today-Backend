import logging

from scalper_today.domain.dtos import PasswordResetRequest, PasswordResetRequestResult
from scalper_today.domain.interfaces import IAuthService, IPasswordResetNotifier, IUserRepository

logger = logging.getLogger(__name__)

PASSWORD_RESET_MESSAGE = (
    "If an account exists for that email, password reset instructions have been generated."
)


class RequestPasswordResetUseCase:
    def __init__(
        self,
        user_repository: IUserRepository,
        auth_service: IAuthService,
        password_reset_notifier: IPasswordResetNotifier | None = None,
    ):
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.password_reset_notifier = password_reset_notifier

    async def execute(self, request: PasswordResetRequest) -> PasswordResetRequestResult:
        email = request.email.lower().strip()
        user = await self.user_repository.get_by_email(email)

        if not user or not user.is_active:
            logger.info("Password reset requested for unknown or inactive account")
            return PasswordResetRequestResult(message=PASSWORD_RESET_MESSAGE)

        reset_token = self.auth_service.create_password_reset_token(user)
        if self.password_reset_notifier:
            try:
                await self.password_reset_notifier.send_password_reset(user.email, reset_token)
            except Exception as exc:
                logger.error(
                    "Password reset email could not be sent",
                    extra={"email": user.email, "error": str(exc)},
                )
        logger.info(f"Password reset requested for user: {user.email}")
        return PasswordResetRequestResult(message=PASSWORD_RESET_MESSAGE, reset_token=reset_token)
