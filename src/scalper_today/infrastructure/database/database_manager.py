import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, database_url: str):
        self._engine: AsyncEngine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")

    async def close(self) -> None:
        await self._engine.dispose()
        logger.info("Database connections closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


def get_db_url(db_path: str = "data/scalper_today.db") -> str:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Use aiosqlite for async SQLite support
    return f"sqlite+aiosqlite:///{path.absolute()}"


async def get_db_session(db_manager: DatabaseManager) -> AsyncGenerator[AsyncSession, None]:
    async with db_manager.session() as session:
        yield session
