import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from ...domain.entities import AuthToken, User
from ...domain.interfaces import IAuthService

logger = logging.getLogger(__name__)


class JWTService(IAuthService):
    def __init__(self, secret_key: str, algorithm: str = "HS256", token_expire_days: int = 30):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expire_days = token_expire_days
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async def hash_password(self, password: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.pwd_context.hash, password)

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.pwd_context.verify, plain_password, hashed_password
        )

    def create_access_token(self, user: User) -> AuthToken:
        expire = datetime.now(UTC) + timedelta(days=self.token_expire_days)

        payload = {
            "sub": user.id,  # Subject (user ID)
            "email": user.email,
            "name": user.name,
            "exp": expire,  # Expiration time
            "iat": datetime.now(UTC),  # Issued at
            "jti": str(uuid.uuid4()),  # JWT ID (unique identifier)
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.info(f"Created access token for user: {user.email}")

        return AuthToken(
            access_token=token,
            token_type="bearer",
            expires_in=self.token_expire_days * 24 * 60 * 60,
        )

    def verify_token(self, token: str) -> dict | None:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            return None

    def get_user_id_from_token(self, token: str) -> str | None:
        payload = self.verify_token(token)
        if payload:
            return payload.get("sub")
        return None
