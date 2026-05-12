import logging

from scalper_today.domain.dtos import PasswordResetConfirmRequest
from scalper_today.domain.exceptions import TokenInvalidError, WeakPasswordError
from scalper_today.domain.interfaces import IAuthService, IUserRepository

from .password_validator import PasswordValidator

logger = logging.getLogger(__name__)


class ConfirmPasswordResetUseCase:
    def __init__(
        self,
        user_repository: IUserRepository,
        auth_service: IAuthService,
        password_validator: PasswordValidator | None = None,
    ):
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.password_validator = password_validator or PasswordValidator()

    async def execute(self, request: PasswordResetConfirmRequest) -> None:
        user_id = self.auth_service.get_user_id_from_password_reset_token(request.token)
        if not user_id:
            raise TokenInvalidError()

        user = await self.user_repository.get_by_id(user_id)
        if not user or not user.is_active:
            raise TokenInvalidError()

        password_result = self.password_validator.validate(request.new_password)
        if not password_result.is_valid:
            raise WeakPasswordError(password_result.errors)

        hashed_password = await self.auth_service.hash_password(request.new_password)
        await self.user_repository.update_password(user.id, hashed_password)

        logger.info(f"Password reset completed for user: {user.email}")
