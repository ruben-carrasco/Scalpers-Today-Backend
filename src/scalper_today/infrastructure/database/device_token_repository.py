import logging
from typing import List
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities import DeviceToken
from ...domain.interfaces import IDeviceTokenRepository
from .models import DeviceTokenModel

logger = logging.getLogger(__name__)


class DeviceTokenRepository(IDeviceTokenRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, device_token: DeviceToken) -> DeviceToken:
        stmt = select(DeviceTokenModel).where(DeviceTokenModel.token == device_token.token)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        # If exists, update
        if existing:
            existing.user_id = device_token.user_id
            existing.device_type = device_token.device_type
            existing.device_name = device_token.device_name
            existing.is_active = True
            existing.last_used_at = datetime.now(timezone.utc)
            await self.session.flush()
            await self.session.refresh(existing)
            logger.info(f"Updated device token for user {device_token.user_id}")
            return self._to_entity(existing)

        # Create new token
        token_model = DeviceTokenModel(
            id=device_token.id,
            user_id=device_token.user_id,
            token=device_token.token,
            device_type=device_token.device_type,
            device_name=device_token.device_name,
            is_active=device_token.is_active,
            created_at=device_token.created_at,
            last_used_at=device_token.last_used_at,
        )

        self.session.add(token_model)
        await self.session.flush()

        logger.info(f"Created device token for user {device_token.user_id}")
        return self._to_entity(token_model)

    async def get_by_user_id(self, user_id: str, active_only: bool = True) -> List[DeviceToken]:
        stmt = None
        result = None
        token_models = None

        if active_only:
            stmt = select(DeviceTokenModel).where(
                and_(DeviceTokenModel.user_id == user_id, DeviceTokenModel.is_active is True)
            )
        else:
            stmt = select(DeviceTokenModel).where(DeviceTokenModel.user_id == user_id)

        result = await self.session.execute(stmt)
        token_models = result.scalars().all()

        return [self._to_entity(model) for model in token_models]

    async def deactivate(self, token: str) -> bool:
        stmt = select(DeviceTokenModel).where(DeviceTokenModel.token == token)
        result = await self.session.execute(stmt)
        token_model = result.scalar_one_or_none()

        if not token_model:
            return False

        token_model.is_active = False

        logger.info(f"Deactivated device token for user {token_model.user_id}")
        return True

    def _to_entity(self, model: DeviceTokenModel) -> DeviceToken:
        entity = DeviceToken(
            id=model.id,
            user_id=model.user_id,
            token=model.token,
            device_type=model.device_type,
            device_name=model.device_name,
            is_active=model.is_active,
            created_at=model.created_at,
            last_used_at=model.last_used_at,
        )
        return entity
