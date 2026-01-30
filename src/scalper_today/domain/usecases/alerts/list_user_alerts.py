import logging
from typing import List

from scalper_today.domain.entities import Alert
from scalper_today.domain.interfaces import IAlertRepository

logger = logging.getLogger(__name__)


class ListUserAlertsUseCase:
    def __init__(self, alert_repository: IAlertRepository):
        self.alert_repository = alert_repository

    async def execute(self, user_id: str, include_deleted: bool = False) -> List[Alert]:
        alerts = await self.alert_repository.get_by_user_id(
            user_id, include_deleted=include_deleted
        )

        logger.info(f"Retrieved {len(alerts)} alerts for user {user_id}")

        return alerts
