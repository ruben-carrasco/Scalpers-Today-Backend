from abc import ABC, abstractmethod

from scalper_today.domain.entities import User


class IUserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User:
        pass

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        pass

    @abstractmethod
    async def create_from_oauth(self, email: str, name: str, provider: str) -> User:
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> bool:
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        pass
