import logging
import uuid
from datetime import UTC, datetime

from scalper_today.domain.dtos import RegisterDeviceTokenRequest
from scalper_today.domain.entities import DeviceToken
from scalper_today.domain.interfaces import IDeviceTokenRepository

logger = logging.getLogger(__name__)


class RegisterDeviceTokenUseCase:
    def __init__(self, device_token_repository: IDeviceTokenRepository):
        self.device_token_repository = device_token_repository

    async def execute(self, request: RegisterDeviceTokenRequest) -> DeviceToken:
        token_str = request.token.strip() if request.token else ""
        device_name = request.device_name.strip() if request.device_name else None
        device_type = request.device_type.lower() if request.device_type else ""
        token_valid = bool(token_str)
        device_type_valid = device_type in ["ios", "android"]
        device_token = None
        registered_token = None

        if not token_valid:
            raise ValueError("Device token is required")

        if not device_type_valid:
            raise ValueError("Device type must be 'ios' or 'android'")

        device_token = DeviceToken(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            token=token_str,
            device_type=device_type,
            device_name=device_name,
            is_active=True,
            created_at=datetime.now(UTC),
            last_used_at=datetime.now(UTC),
        )

        registered_token = await self.device_token_repository.create(device_token)

        logger.info(
            f"Device token registered for user {registered_token.user_id} "
            f"({registered_token.device_type})"
        )

        return registered_token
