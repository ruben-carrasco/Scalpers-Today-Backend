import logging
from datetime import datetime, timezone

from scalper_today.domain.entities import Alert, AlertCondition, AlertType, AlertStatus
from scalper_today.domain.dtos import UpdateAlertRequest
from scalper_today.domain.interfaces import IAlertRepository
from scalper_today.domain.exceptions import ResourceNotFoundError, PermissionDeniedError, ValidationError

logger = logging.getLogger(__name__)


class UpdateAlertUseCase:
    def __init__(self, alert_repository: IAlertRepository):
        self.alert_repository = alert_repository

    async def execute(self, request: UpdateAlertRequest) -> Alert:
        alert = await self.alert_repository.get_by_id(request.alert_id)
        conditions = []
        updated_alert = None

        if not alert:
            raise ResourceNotFoundError("Alert", request.alert_id)

        if alert.user_id != request.user_id:
            raise PermissionDeniedError("You don't have permission to update this alert", action="update_alert")

        if request.name is not None:
            name_empty = not request.name or len(request.name.strip()) == 0
            name_too_long = len(request.name) > 200

            if name_empty:
                raise ValidationError("Alert name cannot be empty")
            if name_too_long:
                raise ValidationError("Alert name must be 200 characters or less")

            alert.name = request.name.strip()

        if request.description is not None:
            alert.description = request.description.strip() if request.description else None

        if request.conditions is not None:
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

            alert.conditions = conditions

        if request.status is not None:
            try:
                alert.status = AlertStatus(request.status)
            except ValueError:
                raise ValidationError(f"Invalid status: {request.status}")

        if request.push_enabled is not None:
            alert.push_enabled = request.push_enabled

        alert.updated_at = datetime.now(timezone.utc)

        updated_alert = await self.alert_repository.update(alert)

        logger.info(f"Alert updated: {updated_alert.name} for user {updated_alert.user_id}")

        return updated_alert
