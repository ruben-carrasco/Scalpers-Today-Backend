from abc import ABC, abstractmethod

from scalper_today.domain.entities import DeviceToken


class IDeviceTokenRepository(ABC):
    @abstractmethod
    async def create(self, token: DeviceToken) -> DeviceToken:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str, active_only: bool = True) -> list[DeviceToken]:
        pass

    @abstractmethod
    async def deactivate(self, token_id: str) -> bool:
        pass
