import json
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.entities import Currency, Language, Timezone, User, UserPreferences
from ....domain.interfaces import IUserRepository
from ..models import UserModel

logger = logging.getLogger(__name__)


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        user_model = UserModel(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            name=user.name,
            avatar_url=user.avatar_url,
            preferences=json.dumps(self._preferences_to_dict(user.preferences)),
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

        self.session.add(user_model)
        await self.session.flush()

        logger.info(f"Created user: {user.email}")
        return self._to_entity(user_model)

    async def get_by_id(self, user_id: str) -> User | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()

        if user_model:
            return self._to_entity(user_model)
        return None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()

        if user_model:
            return self._to_entity(user_model)
        return None

    async def update(self, user: User) -> User:
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()

        if not user_model:
            raise ValueError(f"User not found: {user.id}")

        # Update fields
        user_model.email = user.email
        user_model.hashed_password = user.hashed_password
        user_model.name = user.name
        user_model.avatar_url = user.avatar_url
        user_model.preferences = json.dumps(self._preferences_to_dict(user.preferences))
        user_model.is_active = user.is_active
        user_model.is_verified = user.is_verified
        user_model.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(user_model)

        logger.info(f"Updated user: {user.email}")
        return self._to_entity(user_model)

    async def delete(self, user_id: str) -> bool:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()

        if not user_model:
            return False

        await self.session.delete(user_model)

        logger.info(f"Deleted user: {user_model.email}")
        return True

    async def email_exists(self, email: str) -> bool:
        stmt = select(UserModel.id).where(UserModel.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _to_entity(self, model: UserModel) -> User:
        try:
            preferences_dict = json.loads(model.preferences)
        except (json.JSONDecodeError, TypeError):
            preferences_dict = {}

        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            name=model.name,
            avatar_url=model.avatar_url,
            preferences=self._dict_to_preferences(preferences_dict),
            is_active=model.is_active,
            is_verified=model.is_verified,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _preferences_to_dict(self, prefs: UserPreferences) -> dict:
        return {
            "language": prefs.language.value,
            "currency": prefs.currency.value,
            "timezone": prefs.timezone.value,
        }

    def _dict_to_preferences(self, data: dict) -> UserPreferences:
        try:
            language = Language(data.get("language", Language.ES.value))
        except ValueError:
            language = Language.ES
        try:
            currency = Currency(data.get("currency", Currency.USD.value))
        except ValueError:
            currency = Currency.USD
        try:
            timezone = Timezone(data.get("timezone", Timezone.EUROPE_MADRID.value))
        except ValueError:
            timezone = Timezone.EUROPE_MADRID

        return UserPreferences(language=language, currency=currency, timezone=timezone)
