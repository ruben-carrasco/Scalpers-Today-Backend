import logging
import uuid
from datetime import datetime, timezone

from scalper_today.domain.entities import Alert, AlertCondition, AlertType, AlertStatus
from scalper_today.domain.dtos import CreateAlertRequest
from scalper_today.domain.interfaces import IAlertRepository
from scalper_today.domain.exceptions import ValidationError

logger = logging.getLogger(__name__)


class CreateAlertUseCase:
    def __init__(self, alert_repository: IAlertRepository):
        self.alert_repository = alert_repository

    async def execute(self, request: CreateAlertRequest) -> Alert:
        name = request.name.strip() if request.name else ""
        description = request.description.strip() if request.description else None
        conditions = []
        alert = None
        created_alert = None

        if not name:
            raise ValidationError("Alert name is required")

        if len(request.name) > 200:
            raise ValidationError("Alert name must be 200 characters or less")

        if request.conditions:
            for cond_dict in request.conditions:
                try:
                    alert_type = AlertType(cond_dict["alert_type"])
                    value = cond_dict.get("value")

                    needs_value = alert_type in [
                        AlertType.SPECIFIC_COUNTRY,
                        AlertType.SPECIFIC_CURRENCY,
                    ]
                    if needs_value and not value:
                        raise ValidationError(f"Value required for {alert_type.value}")

                    conditions.append(AlertCondition(alert_type=alert_type, value=value))

                except (KeyError, ValueError) as e:
                    raise ValidationError(f"Invalid condition: {e}")

        if not conditions:
            raise ValidationError("At least one condition is required")

        alert = Alert(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            name=name,
            description=description,
            conditions=conditions,
            status=AlertStatus.ACTIVE,
            push_enabled=request.push_enabled,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            trigger_count=0,
        )

        created_alert = await self.alert_repository.create(alert)

        logger.info(f"Alert created: {created_alert.name} for user {created_alert.user_id}")

        return created_alert
