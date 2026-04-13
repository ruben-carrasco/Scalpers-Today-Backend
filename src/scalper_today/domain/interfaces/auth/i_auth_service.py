from abc import ABC, abstractmethod
from typing import Optional

from scalper_today.domain.entities import User, AuthToken


class IAuthService(ABC):
    @abstractmethod
    async def hash_password(self, password: str) -> str:
        pass

    @abstractmethod
    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        pass

    @abstractmethod
    def create_access_token(self, user: User) -> AuthToken:
        pass

    @abstractmethod
    def get_user_id_from_token(self, token: str) -> Optional[str]:
        pass
