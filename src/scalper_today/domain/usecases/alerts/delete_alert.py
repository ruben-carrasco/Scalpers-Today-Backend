import logging

from scalper_today.domain.exceptions import PermissionDeniedError, ResourceNotFoundError
from scalper_today.domain.interfaces import IAlertRepository

logger = logging.getLogger(__name__)


class DeleteAlertUseCase:
    def __init__(self, alert_repository: IAlertRepository):
        self.alert_repository = alert_repository

    async def execute(self, alert_id: str, user_id: str, soft_delete: bool = True) -> bool:
        alert = await self.alert_repository.get_by_id(alert_id)

        if not alert:
            raise ResourceNotFoundError("Alert", alert_id)

        if alert.user_id != user_id:
            raise PermissionDeniedError(
                "You don't have permission to delete this alert", action="delete_alert"
            )

        success = await self.alert_repository.delete(alert_id, soft_delete=soft_delete)

        if success:
            logger.info(f"Alert deleted: {alert.name} for user {user_id}")

        return success
