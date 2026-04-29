import logging
from google.oauth2 import id_token
from google.auth.transport import requests
from scalper_today.config import Settings
from scalper_today.domain.interfaces import IUserRepository, IAuthService
from scalper_today.domain.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class GoogleLoginUseCase:
    def __init__(
        self, user_repository: IUserRepository, auth_service: IAuthService, settings: Settings
    ):
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.settings = settings

    async def execute(self, id_token_str: str) -> dict:
        try:
            # Verify the token
            id_info = id_token.verify_oauth2_token(
                id_token_str, requests.Request(), self.settings.google_client_id
            )
            email = id_info["email"]
            name = id_info.get("name", "")

            user = await self.user_repository.get_by_email(email)

            if not user:
                # Create user if doesn't exist
                # Assign default preferences
                user = await self.user_repository.create_from_oauth(email, name, provider="google")

            token = self.auth_service.create_access_token(user)
            return {"user": user, "token": token}

        except Exception as e:
            logger.error(f"Google login failed: {e}")
            raise AuthenticationError("Invalid Google token")
