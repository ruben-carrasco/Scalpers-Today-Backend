from abc import ABC, abstractmethod


class IPasswordResetNotifier(ABC):
    @abstractmethod
    async def send_password_reset(self, email: str, token: str) -> None:
        pass
