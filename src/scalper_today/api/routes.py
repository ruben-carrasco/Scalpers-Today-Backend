import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text

from scalper_today.api.dependencies import Container, get_container
from scalper_today.domain.entities import DailyBriefing, EconomicEvent
from scalper_today.domain.usecases import (
    EventFilter,
    EventFilterCriteria,
    GetHomeSummaryUseCase,
    GetUpcomingEventsUseCase,
    GetAvailableCountriesUseCase,
)
from .schemas import (
    EventResponse,
    HomeSummaryResponse,
    DailyBriefingResponse,
    HealthCheckResponse,
    FilteredEventsResponse,
    ImportanceEventsResponse,
    UpcomingEventsResponse,
    AvailableCountriesResponse,
    RefreshEventsResponse,
    StatusResponse,
    ReadinessResponse,
    WelcomeSchema,
    TodayStatsSchema,
    MarketSentimentSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency type alias for cleaner route signatures
ContainerDep = Annotated[Container, Depends(get_container)]


@router.get(
    "/macro",
    tags=["Events"],
    summary="Get Economic Events",
    response_model=List[EventResponse],
    responses={
        200: {
            "description": "List of economic events retrieved successfully.",
        },
        500: {"description": "Internal server error fetching events."},
    },
)
async def get_macro_events(c: ContainerDep) -> List[EconomicEvent]:
    return await c.get_macro_events()


@router.post(
    "/macro/refresh",
    tags=["Events"],
    summary="Force Refresh Events",
    response_model=RefreshEventsResponse,
    responses={
        200: {"description": "Events refreshed successfully."},
        403: {"description": "Invalid or missing API key."},
    },
)
async def refresh_macro_events(
    c: ContainerDep,
    api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
) -> RefreshEventsResponse:
    expected_key = c.settings.refresh_api_key
    if not expected_key or api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

    logger.info("Force refreshing events from source...")
    events = await c.get_macro_events(force_refresh=True)
    return RefreshEventsResponse(
        status="success",
        message=f"Refreshed {len(events)} events",
        count=len(events),
    )


@router.get(
    "/brief", tags=["Briefing"], summary="Get Daily Briefing", response_model=DailyBriefingResponse
)
async def get_daily_briefing(c: ContainerDep) -> DailyBriefing:
    return await c.get_daily_briefing()


@router.get("/health", tags=["System"], summary="Health Check", response_model=HealthCheckResponse)
async def health_check(c: ContainerDep) -> HealthCheckResponse:
    # Logic kept here because it's a system check, but we could move it to a use case
    database_status = "unknown"
    ai_service_status = "configured" if c.settings.is_ai_configured else "not_configured"

    try:
        async with c.database_manager.session() as session:
            await session.execute(text("SELECT 1"))
            database_status = "healthy"
    except Exception as e:
        database_status = "unhealthy"
        logger.error(f"Database health check failed: {e}")

    return HealthCheckResponse(
        status="healthy" if database_status == "healthy" else "degraded",
        version=c.settings.app_version,
        environment=c.settings.app_env,
        checks={
            "database": database_status,
            "ai_service": ai_service_status,
        },
    )


@router.get(
    "/health/live", tags=["System"], summary="Liveness Probe", response_model=StatusResponse
)
async def liveness_probe() -> StatusResponse:
    return StatusResponse(status="alive")


@router.get(
    "/health/ready", tags=["System"], summary="Readiness Probe", response_model=ReadinessResponse
)
async def readiness_probe(c: ContainerDep) -> ReadinessResponse:
    is_ready = True
    checks = {}

    try:
        async with c.database_manager.session() as session:
            await session.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception:
        checks["database"] = False
        is_ready = False

    checks["ai_configured"] = c.settings.is_ai_configured

    status = "ready" if is_ready else "not_ready"

    if not is_ready:
        raise HTTPException(status_code=503, detail={"status": status, "checks": checks})

    return ReadinessResponse(status=status, checks=checks)


@router.get(
    "/home/summary",
    tags=["Mobile - Home"],
    summary="Home Screen Summary",
    response_model=HomeSummaryResponse,
)
async def get_home_summary(c: ContainerDep):
    events = await c.get_macro_events()

    try:
        briefing = await c.get_daily_briefing()
    except Exception as e:
        logger.error(f"/home/summary briefing error (using fallback): {e}")
        briefing = DailyBriefing.error("Briefing temporalmente no disponible")

    use_case = GetHomeSummaryUseCase()
    summary = use_case.execute(events, briefing)

    # Manual mapping to the response model to handle the nested structure
    return HomeSummaryResponse(
        welcome=WelcomeSchema(
            greeting=summary.greeting, date=summary.date_formatted, time=summary.time_formatted
        ),
        today_stats=TodayStatsSchema(
            total_events=summary.total_events,
            high_impact=summary.high_impact_count,
            medium_impact=summary.medium_impact_count,
            low_impact=summary.low_impact_count,
        ),
        next_event=summary.next_event,
        market_sentiment=MarketSentimentSchema(
            overall=summary.sentiment, volatility=summary.volatility_level
        ),
        highlights=summary.highlights,
    )


@router.get(
    "/events/filtered",
    tags=["Mobile - Events"],
    summary="Filtered Events",
    response_model=FilteredEventsResponse,
)
async def get_filtered_events(
    c: ContainerDep,
    importance: Annotated[Optional[int], Query(ge=1, le=3)] = None,
    country: Annotated[Optional[str], Query()] = None,
    has_data: Annotated[Optional[bool], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
) -> FilteredEventsResponse:
    events = await c.get_macro_events()

    criteria = EventFilterCriteria(
        importance=importance, country=country, has_data=has_data, search=search
    )
    filtered = EventFilter.apply_criteria(events, criteria)

    return FilteredEventsResponse(total=len(filtered), filters_applied=criteria, events=filtered)


@router.get(
    "/events/by-importance/{importance}",
    tags=["Mobile - Events"],
    summary="Events by Importance",
    response_model=ImportanceEventsResponse,
    responses={400: {"description": "Invalid importance level provided. Must be 1, 2, or 3."}},
)
async def get_events_by_importance(
    importance: int,
    c: ContainerDep,
) -> ImportanceEventsResponse:
    if importance not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Importance must be 1, 2, or 3")

    events = await c.get_macro_events()
    filtered = EventFilter.by_importance(events, importance)

    return ImportanceEventsResponse(
        importance=importance,
        count=len(filtered),
        events=filtered,
    )


@router.get(
    "/events/upcoming",
    tags=["Mobile - Events"],
    summary="Upcoming Events",
    response_model=UpcomingEventsResponse,
)
async def get_upcoming_events(
    c: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
):
    events = await c.get_macro_events()

    use_case = GetUpcomingEventsUseCase()
    result = use_case.execute(events, limit=limit)

    return result


@router.get(
    "/config/countries",
    tags=["Mobile - Config"],
    summary="Available Countries",
    response_model=AvailableCountriesResponse,
)
async def get_available_countries(c: ContainerDep):
    events = await c.get_macro_events()

    use_case = GetAvailableCountriesUseCase()
    result = use_case.execute(events)

    return result
