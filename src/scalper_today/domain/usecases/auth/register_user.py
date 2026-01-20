import logging
import re
import uuid
from datetime import datetime, timezone

from scalper_today.domain.entities import User, UserPreferences, Language, Currency, Timezone
from scalper_today.domain.dtos import RegisterUserRequest, RegisterUserResponse
from scalper_today.domain.interfaces import IUserRepository, IAuthService
from scalper_today.domain.exceptions import (
    InvalidEmailError,
    WeakPasswordError,
    DuplicateEmailError,
)
from .password_validator import PasswordValidator

logger = logging.getLogger(__name__)


class RegisterUserUseCase:
    EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    def __init__(
        self,
        user_repository: IUserRepository,
        auth_service: IAuthService,
        password_validator: PasswordValidator = None,
    ):
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.password_validator = password_validator or PasswordValidator()

    async def execute(self, request: RegisterUserRequest) -> RegisterUserResponse:
        email = request.email.lower().strip()
        name = request.name.strip()
        email_valid = self._is_valid_email(email)
        password_result = self.password_validator.validate(request.password)
        email_exists = False
        hashed_password = None
        preferences = None
        user = None
        created_user = None
        token = None

        if not email_valid:
            raise InvalidEmailError(email)

        if not password_result.is_valid:
            raise WeakPasswordError(password_result.errors)

        email_exists = await self.user_repository.email_exists(email)
        if email_exists:
            raise DuplicateEmailError(request.email)

        hashed_password = await self.auth_service.hash_password(request.password)

        try:
            lang = Language(request.language)
        except ValueError:
            lang = Language.ES

        try:
            curr = Currency(request.currency)
        except ValueError:
            curr = Currency.USD

        try:
            tz = Timezone(request.timezone)
        except ValueError:
            tz = Timezone.EUROPE_MADRID

        preferences = UserPreferences(
            language=lang,
            currency=curr,
            timezone=tz,
        )

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hashed_password,
            name=name,
            preferences=preferences,
            is_active=True,
            is_verified=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        created_user = await self.user_repository.create(user)

        token = self.auth_service.create_access_token(created_user)

        logger.info(f"User registered successfully: {created_user.email}")

        response = RegisterUserResponse(user=created_user, token=token)
        return response

    def _is_valid_email(self, email: str) -> bool:
        match = re.match(self.EMAIL_PATTERN, email)
        is_valid = match is not None

        return is_valid
