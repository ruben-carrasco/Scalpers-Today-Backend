from abc import ABC, abstractmethod

from scalper_today.domain.entities import Alert


class IAlertRepository(ABC):
    @abstractmethod
    async def create(self, alert: Alert) -> Alert:
        pass

    @abstractmethod
    async def get_by_id(self, alert_id: str) -> Alert | None:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str, include_deleted: bool = False) -> list[Alert]:
        pass

    @abstractmethod
    async def update(self, alert: Alert) -> Alert:
        pass

    @abstractmethod
    async def delete(self, alert_id: str, hard_delete: bool = False) -> bool:
        pass
