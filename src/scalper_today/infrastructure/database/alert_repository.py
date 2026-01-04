import json
import logging
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities import Alert, AlertCondition, AlertStatus, AlertType
from ...domain.interfaces import IAlertRepository
from .models import AlertModel

logger = logging.getLogger(__name__)


class AlertRepository(IAlertRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, alert: Alert) -> Alert:
        conditions_json = json.dumps([self._condition_to_dict(c) for c in alert.conditions])

        alert_model = AlertModel(
            id=alert.id,
            user_id=alert.user_id,
            name=alert.name,
            description=alert.description,
            conditions=conditions_json,
            status=alert.status.value,
            push_enabled=alert.push_enabled,
            trigger_count=alert.trigger_count,
            last_triggered_at=alert.last_triggered_at,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )

        self.session.add(alert_model)
        await self.session.flush()

        logger.info(f"Created alert: {alert.name} for user {alert.user_id}")
        return self._to_entity(alert_model)

    async def get_by_id(self, alert_id: str) -> Optional[Alert]:
        stmt = select(AlertModel).where(AlertModel.id == alert_id)
        result = await self.session.execute(stmt)
        alert_model = result.scalar_one_or_none()

        if alert_model:
            return self._to_entity(alert_model)
        return None

    async def get_by_user_id(self, user_id: str, include_deleted: bool = False) -> List[Alert]:
        if include_deleted:
            stmt = select(AlertModel).where(AlertModel.user_id == user_id)
        else:
            stmt = select(AlertModel).where(
                and_(AlertModel.user_id == user_id, AlertModel.status != AlertStatus.DELETED.value)
            )

        result = await self.session.execute(stmt)
        alert_models = result.scalars().all()

        return [self._to_entity(model) for model in alert_models]

    async def get_active_alerts(self) -> List[Alert]:
        stmt = select(AlertModel).where(
            and_(AlertModel.status == AlertStatus.ACTIVE.value, AlertModel.push_enabled is True)
        )
        result = await self.session.execute(stmt)
        alert_models = result.scalars().all()

        return [self._to_entity(model) for model in alert_models]

    async def update(self, alert: Alert) -> Alert:
        stmt = select(AlertModel).where(AlertModel.id == alert.id)
        result = await self.session.execute(stmt)
        alert_model = result.scalar_one_or_none()

        if not alert_model:
            raise ValueError(f"Alert not found: {alert.id}")

        # Update fields
        alert_model.name = alert.name
        alert_model.description = alert.description
        alert_model.conditions = json.dumps([self._condition_to_dict(c) for c in alert.conditions])
        alert_model.status = alert.status.value
        alert_model.push_enabled = alert.push_enabled
        alert_model.trigger_count = alert.trigger_count
        alert_model.last_triggered_at = alert.last_triggered_at
        alert_model.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(alert_model)

        logger.info(f"Updated alert: {alert.name}")
        return self._to_entity(alert_model)

    async def delete(self, alert_id: str, soft_delete: bool = True) -> bool:
        stmt = select(AlertModel).where(AlertModel.id == alert_id)
        result = await self.session.execute(stmt)
        alert_model = result.scalar_one_or_none()

        if not alert_model:
            return False

        if soft_delete:
            alert_model.status = AlertStatus.DELETED.value
            alert_model.updated_at = datetime.now(timezone.utc)
            logger.info(f"Soft deleted alert: {alert_model.name}")
        else:
            await self.session.delete(alert_model)
            logger.info(f"Hard deleted alert: {alert_model.name}")

        return True

    async def increment_trigger_count(self, alert_id: str) -> None:
        stmt = select(AlertModel).where(AlertModel.id == alert_id)
        result = await self.session.execute(stmt)
        alert_model = result.scalar_one_or_none()

        if alert_model:
            alert_model.trigger_count += 1
            alert_model.last_triggered_at = datetime.now(timezone.utc)

    def _to_entity(self, model: AlertModel) -> Alert:
        conditions_list = []

        try:
            conditions_list = json.loads(model.conditions)
        except (json.JSONDecodeError, TypeError):
            conditions_list = []

        alert = Alert(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            description=model.description,
            conditions=[self._dict_to_condition(c) for c in conditions_list],
            status=AlertStatus(model.status),
            push_enabled=model.push_enabled,
            trigger_count=model.trigger_count,
            last_triggered_at=model.last_triggered_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        return alert

    def _condition_to_dict(self, condition: AlertCondition) -> dict:
        return {"alert_type": condition.alert_type.value, "value": condition.value}

    def _dict_to_condition(self, data: dict) -> AlertCondition:
        alert_type = AlertType(data["alert_type"])
        value = data.get("value")
        return AlertCondition(alert_type=alert_type, value=value)
