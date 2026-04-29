import logging

from scalper_today.domain.entities import User
from scalper_today.domain.interfaces import IAuthService, IUserRepository

logger = logging.getLogger(__name__)


class GetCurrentUserUseCase:
    def __init__(self, user_repository: IUserRepository, auth_service: IAuthService):
        self.user_repository = user_repository
        self.auth_service = auth_service

    async def execute(self, token: str) -> User | None:
        user_id = self.auth_service.get_user_id_from_token(token)

        if not user_id:
            logger.warning("Invalid or expired token")
            return None

        user = await self.user_repository.get_by_id(user_id)

        if not user:
            logger.warning(f"User not found for token: {user_id}")
            return None

        if not user.is_active:
            logger.warning(f"Token used for inactive user: {user.email}")
            return None

        return user
