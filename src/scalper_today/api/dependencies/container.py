import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator, Optional, List

import httpx
import pytz
from sqlalchemy.ext.asyncio import AsyncSession

from scalper_today.domain.interfaces import (
    IAIAnalyzer,
    IAuthService,
    IEventRepository,
    IEventScraper,
    IUserRepository,
    IAlertRepository,
    IDeviceTokenRepository,
)
from scalper_today.domain.entities import EconomicEvent, DailyBriefing, HomeSummary
from scalper_today.domain.usecases import GetDailyBriefingUseCase, GetHomeSummaryUseCase, GetMacroEventsUseCase
from scalper_today.config import Settings, get_settings
from scalper_today.infrastructure import InvestingComScraper, OpenRouterAnalyzer
from scalper_today.infrastructure.database import (
    DatabaseManager,
    EventRepository,
    UserRepository,
    AlertRepository,
    DeviceTokenRepository,
    get_db_url,
)
from scalper_today.infrastructure.auth import JWTService
from scalper_today.infrastructure.notifications.expo import ExpoPushService
from scalper_today.infrastructure.notifications.notification_scheduler import NotificationScheduler

logger = logging.getLogger(__name__)
TZ_MADRID = pytz.timezone("Europe/Madrid")


class Container:
    _instance: "Container | None" = None

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient,
        database_manager: DatabaseManager,
        scraper: IEventScraper,
        analyzer: IAIAnalyzer,
        jwt_service: IAuthService,
        expo_push_service: Optional[ExpoPushService] = None,
        notification_scheduler: Optional[NotificationScheduler] = None,
    ):
        self.settings = settings
        self.http_client = http_client
        self.database_manager = database_manager
        self.scraper: IEventScraper = scraper
        self.analyzer: IAIAnalyzer = analyzer
        self._jwt_service: IAuthService = jwt_service
        self._expo_push_service = expo_push_service
        self._notification_scheduler = notification_scheduler

    def get_jwt_service(self) -> IAuthService:
        return self._jwt_service

    def get_expo_push_service(self) -> Optional[ExpoPushService]:
        return self._expo_push_service

    def get_notification_scheduler(self) -> Optional[NotificationScheduler]:
        return self._notification_scheduler

    def get_user_repository(self, session: AsyncSession) -> IUserRepository:
        return UserRepository(session)

    def get_event_repository(self, session: AsyncSession) -> IEventRepository:
        return EventRepository(session)

    def get_alert_repository(self, session: AsyncSession) -> IAlertRepository:
        return AlertRepository(session)

    def get_device_token_repository(self, session: AsyncSession) -> IDeviceTokenRepository:
        return DeviceTokenRepository(session)

    async def get_macro_events(self, force_refresh: bool = False) -> List[EconomicEvent]:
        madrid_date = datetime.now(TZ_MADRID).date()
        async with self.database_manager.session() as session:
            repository = self.get_event_repository(session)
            use_case = GetMacroEventsUseCase(
                self.scraper, repository, self.analyzer, target_date=madrid_date
            )
            return await use_case.execute(force_refresh=force_refresh)

    async def get_daily_briefing(self) -> DailyBriefing:
        madrid_date = datetime.now(TZ_MADRID).date()
        async with self.database_manager.session() as session:
            repository = self.get_event_repository(session)
            use_case = GetDailyBriefingUseCase(
                self.scraper, repository, self.analyzer, target_date=madrid_date
            )
            return await use_case.execute()

    async def get_home_summary(self) -> HomeSummary:
        events = await self.get_macro_events()

        try:
            briefing = await self.get_daily_briefing()
        except Exception as e:
            logger.error(f"Home summary briefing error (using fallback): {e}")
            briefing = DailyBriefing.error("Briefing temporalmente no disponible")

        use_case = GetHomeSummaryUseCase()
        return use_case.execute(events, briefing)

    @classmethod
    def get_instance(cls) -> "Container":
        if cls._instance is None:
            raise RuntimeError("Container not initialized")
        return cls._instance


def get_container() -> Container:
    return Container.get_instance()


@asynccontextmanager
async def init_container() -> AsyncIterator[Container]:
    logger.info("Initializing container...")
    settings = get_settings()

    if not settings.is_ai_configured:
        logger.warning("⚠️  OPENROUTER_API_KEY not set - AI features disabled!")

    if not settings.is_auth_configured:
        logger.warning("⚠️  JWT_SECRET_KEY not properly set - Using development mode (insecure!)")

    db_url = get_db_url(settings.database_path)
    db_manager = DatabaseManager(db_url)
    await db_manager.create_tables()
    logger.info(f"Database initialized: {settings.database_path}")

    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout_seconds),
        follow_redirects=True,
    )

    scraper = InvestingComScraper(settings, http_client)
    analyzer = OpenRouterAnalyzer(settings, http_client)

    # SECURITY: Fail fast if no secret key in production
    jwt_secret = settings.jwt_secret_key
    if not jwt_secret:
        if settings.app_env == "production":
            raise RuntimeError("JWT_SECRET_KEY must be set in production environment")
        jwt_secret = "dev-secret-key-change-in-production"
        logger.warning("Using insecure development JWT secret - DO NOT use in production!")

    jwt_service = JWTService(
        secret_key=jwt_secret,
        algorithm=settings.jwt_algorithm,
        token_expire_days=settings.jwt_token_expire_days,
    )

    expo_push_service = ExpoPushService(http_client)
    notification_scheduler = NotificationScheduler(
        expo_push_service=expo_push_service,
        database_manager=db_manager,
        check_interval_seconds=settings.notification_check_interval,
        notify_before_minutes=settings.notification_before_minutes,
    )

    container = Container(
        settings=settings,
        http_client=http_client,
        database_manager=db_manager,
        scraper=scraper,
        analyzer=analyzer,
        jwt_service=jwt_service,
        expo_push_service=expo_push_service,
        notification_scheduler=notification_scheduler,
    )

    Container._instance = container

    await notification_scheduler.start()

    logger.info(
        f"Container ready. Database: {settings.database_path}, "
        f"AI: {settings.is_ai_configured}, Auth: {settings.is_auth_configured}, "
        f"Notifications: enabled"
    )

    try:
        yield container
    finally:
        logger.info("Shutting down container...")
        await notification_scheduler.stop()
        await http_client.aclose()
        await db_manager.close()
        Container._instance = None
