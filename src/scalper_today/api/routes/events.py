import logging
import time
from collections import defaultdict
from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security
from fastapi.security import APIKeyHeader

from scalper_today.api.dependencies import Container, get_container
from scalper_today.domain.entities import EconomicEvent
from scalper_today.domain.usecases import (
    EventFilter,
    EventFilterCriteria,
    GetUpcomingEventsUseCase,
    GetAvailableCountriesUseCase,
)
from ..schemas import (
    EventResponse,
    WeekEventResponse,
    HomeSummaryResponse,
    DailyBriefingResponse,
    FilteredEventsResponse,
    ImportanceEventsResponse,
    UpcomingEventsResponse,
    AvailableCountriesResponse,
    RefreshEventsResponse,
    WelcomeSchema,
    TodayStatsSchema,
    MarketSentimentSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Dependency type alias for cleaner route signatures
ContainerDep = Annotated[Container, Depends(get_container)]

# Refresh endpoint anti-abuse rate limit
_refresh_rate_limit_store: dict[str, list[float]] = defaultdict(list)
REFRESH_RATE_LIMIT_MAX_ATTEMPTS = 10
REFRESH_RATE_LIMIT_WINDOW_SECONDS = 60
MAX_WEEK_RANGE_DAYS = 31


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    return request.client.host if request.client else "unknown"


def _check_refresh_rate_limit(request: Request) -> None:
    client_ip = _get_client_ip(request)
    key = f"{client_ip}:{request.url.path}"
    now = time.monotonic()
    attempts = _refresh_rate_limit_store[key]
    _refresh_rate_limit_store[key] = [
        t for t in attempts if now - t < REFRESH_RATE_LIMIT_WINDOW_SECONDS
    ]

    if len(_refresh_rate_limit_store[key]) >= REFRESH_RATE_LIMIT_MAX_ATTEMPTS:
        logger.warning("Refresh rate limit exceeded", extra={"ip": client_ip})
        raise HTTPException(status_code=429, detail="Too many refresh requests. Try again later.")

    _refresh_rate_limit_store[key].append(now)


def _resolve_event_range(
    start_date: Optional[date],
    end_date: Optional[date],
) -> tuple[Optional[date], Optional[date]]:
    if start_date is None and end_date is None:
        return None, None

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=422, detail="startDate and endDate must be provided together"
        )

    if end_date < start_date:
        raise HTTPException(
            status_code=422, detail="endDate must be greater than or equal to startDate"
        )

    range_days = (end_date - start_date).days + 1
    if range_days > MAX_WEEK_RANGE_DAYS:
        raise HTTPException(
            status_code=422, detail=f"Date range cannot exceed {MAX_WEEK_RANGE_DAYS} days"
        )

    return start_date, end_date


@router.get(
    "/macro",
    tags=["Events"],
    summary="Get Economic Events",
    description=(
        "Returns today's normalized economic events. "
        "If the upstream provider has no data and local cache is empty, returns `503`."
    ),
    response_model=List[EventResponse],
    responses={
        200: {
            "description": "List of economic events retrieved successfully.",
        },
        503: {"description": "Economic events temporarily unavailable."},
        500: {"description": "Internal server error fetching events."},
    },
)
async def get_macro_events(c: ContainerDep) -> List[EconomicEvent]:
    events = await c.get_macro_events()
    if not events:
        raise HTTPException(status_code=503, detail="Economic events temporarily unavailable")
    return events


@router.post(
    "/macro/refresh",
    tags=["Events"],
    summary="Force Refresh Events",
    description=(
        "Forces a provider refresh and cache update for today's events. "
        "Requires `X-API-Key` header."
    ),
    response_model=RefreshEventsResponse,
    responses={
        200: {"description": "Events refreshed successfully."},
        403: {"description": "Invalid or missing API key."},
        429: {"description": "Too many refresh requests."},
    },
)
async def refresh_macro_events(
    c: ContainerDep,
    req: Request,
    api_key: Annotated[Optional[str], Security(api_key_header)] = None,
) -> RefreshEventsResponse:
    _check_refresh_rate_limit(req)
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
async def get_daily_briefing(c: ContainerDep) -> DailyBriefingResponse:
    return await c.get_daily_briefing()


@router.get(
    "/home/summary",
    tags=["Mobile - Home"],
    summary="Home Screen Summary",
    response_model=HomeSummaryResponse,
)
async def get_home_summary(c: ContainerDep):
    summary = await c.get_home_summary()

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
    country: Annotated[Optional[str], Query(max_length=100)] = None,
    has_data: Annotated[Optional[bool], Query()] = None,
    search: Annotated[Optional[str], Query(min_length=1, max_length=200)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> FilteredEventsResponse:
    events = await c.get_macro_events()

    criteria = EventFilterCriteria(
        importance=importance, country=country, has_data=has_data, search=search
    )
    filtered = EventFilter.apply_criteria(events, criteria)
    paginated = filtered[offset : offset + limit]

    return FilteredEventsResponse(total=len(filtered), filters_applied=criteria, events=paginated)


@router.get(
    "/events/week",
    tags=["Mobile - Events"],
    summary="Weekly Events",
    description=(
        "Returns events for the current week by default. "
        "Optionally accepts `startDate` and `endDate` in YYYY-MM-DD format."
    ),
    response_model=List[WeekEventResponse],
)
async def get_week_events(
    c: ContainerDep,
    start_date: Annotated[Optional[date], Query(alias="startDate")] = None,
    end_date: Annotated[Optional[date], Query(alias="endDate")] = None,
) -> List[WeekEventResponse]:
    resolved_start, resolved_end = _resolve_event_range(start_date, end_date)
    events = await c.get_week_events(start_date=resolved_start, end_date=resolved_end)
    return [WeekEventResponse.from_domain(event) for event in events]


@router.post(
    "/events/week/refresh",
    tags=["Mobile - Events"],
    summary="Force Refresh Weekly Events",
    description=(
        "Forces a provider refresh and cache update for the current week. "
        "Requires `X-API-Key` header."
    ),
    response_model=RefreshEventsResponse,
    responses={
        200: {"description": "Weekly events refreshed successfully."},
        403: {"description": "Invalid or missing API key."},
        429: {"description": "Too many refresh requests."},
    },
)
async def refresh_week_events(
    c: ContainerDep,
    req: Request,
    start_date: Annotated[Optional[date], Query(alias="startDate")] = None,
    end_date: Annotated[Optional[date], Query(alias="endDate")] = None,
    api_key: Annotated[Optional[str], Security(api_key_header)] = None,
) -> RefreshEventsResponse:
    _check_refresh_rate_limit(req)
    expected_key = c.settings.refresh_api_key
    if not expected_key or api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

    resolved_start, resolved_end = _resolve_event_range(start_date, end_date)
    logger.info("Force refreshing week events from source...")
    events = await c.get_week_events(
        force_refresh=True,
        start_date=resolved_start,
        end_date=resolved_end,
    )
    return RefreshEventsResponse(
        status="success",
        message=f"Refreshed {len(events)} weekly events",
        count=len(events),
    )


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
