import logging
import time
from collections import defaultdict
from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Security
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
    ErrorResponse,
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
    summary="Get today's economic events",
    description=(
        "Returns today's normalized economic events in Madrid time. The response is served from "
        "cache when valid and falls back to the configured provider when refresh is needed."
    ),
    response_model=List[EventResponse],
    responses={
        200: {"description": "Economic events retrieved successfully."},
        503: {"model": ErrorResponse, "description": "Events temporarily unavailable."},
        500: {"model": ErrorResponse, "description": "Internal server error fetching events."},
    },
)
async def get_macro_events(c: ContainerDep) -> List[EconomicEvent]:
    events = await c.get_macro_events()
    if not events:
        raise HTTPException(status_code=503, detail="Economic events temporarily unavailable")
    return events


@router.post(
    "/macro/refresh",
    tags=["Admin - Refresh"],
    summary="Refresh today's economic events",
    description=(
        "Forces a provider refresh and cache update for today's events. Requires the `X-API-Key` "
        "header and is rate-limited to protect external provider quota."
    ),
    response_model=RefreshEventsResponse,
    responses={
        200: {"description": "Events refreshed successfully."},
        403: {"model": ErrorResponse, "description": "Invalid or missing API key."},
        429: {"model": ErrorResponse, "description": "Too many refresh requests."},
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
    "/brief",
    tags=["Briefing"],
    summary="Get daily AI briefing",
    description="Returns the AI-generated market briefing for today's macroeconomic context.",
    response_model=DailyBriefingResponse,
    responses={200: {"description": "Daily briefing returned successfully."}},
)
async def get_daily_briefing(c: ContainerDep) -> DailyBriefingResponse:
    return await c.get_daily_briefing()


@router.get(
    "/home/summary",
    tags=["Mobile - Home"],
    summary="Get mobile home summary",
    description=(
        "Returns the compact payload used by the mobile home screen: greeting, event counters, "
        "next event, sentiment, volatility, and highlights."
    ),
    response_model=HomeSummaryResponse,
    responses={200: {"description": "Home summary returned successfully."}},
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
    summary="Filter today's events",
    description=(
        "Filters today's economic events by importance, country, data availability, and text "
        "search. Supports offset/limit pagination for mobile lists."
    ),
    response_model=FilteredEventsResponse,
    responses={
        200: {"description": "Filtered events returned successfully."},
        422: {"model": ErrorResponse, "description": "Invalid filter or pagination parameter."},
    },
)
async def get_filtered_events(
    c: ContainerDep,
    importance: Annotated[
        Optional[int], Query(ge=1, le=3, description="Importance level: 1 low, 2 medium, 3 high.")
    ] = None,
    country: Annotated[
        Optional[str], Query(max_length=100, description="Country or currency code to match.")
    ] = None,
    has_data: Annotated[
        Optional[bool], Query(description="When true, only events with released actual values.")
    ] = None,
    search: Annotated[
        Optional[str], Query(min_length=1, max_length=200, description="Text search over titles.")
    ] = None,
    offset: Annotated[int, Query(ge=0, description="Zero-based pagination offset.")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum events to return.")] = 50,
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
    summary="Get events by weekly date range",
    description=(
        "Returns events for the current week by default. Optionally accepts `startDate` and "
        "`endDate` in `YYYY-MM-DD` format. Custom ranges are limited to 31 days."
    ),
    response_model=List[WeekEventResponse],
    responses={
        200: {"description": "Weekly events returned successfully."},
        422: {"model": ErrorResponse, "description": "Invalid or incomplete date range."},
    },
)
async def get_week_events(
    c: ContainerDep,
    start_date: Annotated[
        Optional[date], Query(alias="startDate", description="Inclusive range start date.")
    ] = None,
    end_date: Annotated[
        Optional[date], Query(alias="endDate", description="Inclusive range end date.")
    ] = None,
) -> List[WeekEventResponse]:
    resolved_start, resolved_end = _resolve_event_range(start_date, end_date)
    events = await c.get_week_events(start_date=resolved_start, end_date=resolved_end)
    return [WeekEventResponse.from_domain(event) for event in events]


@router.post(
    "/events/week/refresh",
    tags=["Admin - Refresh"],
    summary="Refresh events by weekly date range",
    description=(
        "Forces a provider refresh and cache update for the current week or a custom date range. "
        "Requires the `X-API-Key` header and is rate-limited to protect external provider quota."
    ),
    response_model=RefreshEventsResponse,
    responses={
        200: {"description": "Weekly events refreshed successfully."},
        403: {"model": ErrorResponse, "description": "Invalid or missing API key."},
        422: {"model": ErrorResponse, "description": "Invalid or incomplete date range."},
        429: {"model": ErrorResponse, "description": "Too many refresh requests."},
    },
)
async def refresh_week_events(
    c: ContainerDep,
    req: Request,
    start_date: Annotated[
        Optional[date], Query(alias="startDate", description="Inclusive range start date.")
    ] = None,
    end_date: Annotated[
        Optional[date], Query(alias="endDate", description="Inclusive range end date.")
    ] = None,
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
    summary="Get events by importance",
    description="Returns today's economic events filtered by impact level.",
    response_model=ImportanceEventsResponse,
    responses={
        200: {"description": "Events filtered by importance returned successfully."},
        400: {"model": ErrorResponse, "description": "Importance must be 1, 2, or 3."},
    },
)
async def get_events_by_importance(
    importance: Annotated[
        int,
        Path(ge=1, le=3, description="Importance level: 1 low, 2 medium, 3 high."),
    ],
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
    summary="Get upcoming events",
    description="Returns the next upcoming events from today's calendar, ordered by time.",
    response_model=UpcomingEventsResponse,
    responses={
        200: {"description": "Upcoming events returned successfully."},
        422: {"model": ErrorResponse, "description": "Invalid limit parameter."},
    },
)
async def get_upcoming_events(
    c: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=20, description="Maximum upcoming events to return.")] = 5,
):
    events = await c.get_macro_events()

    use_case = GetUpcomingEventsUseCase()
    result = use_case.execute(events, limit=limit)

    return result


@router.get(
    "/config/countries",
    tags=["Mobile - Config"],
    summary="Get available countries",
    description="Returns the countries/currencies currently present in today's calendar data.",
    response_model=AvailableCountriesResponse,
    responses={200: {"description": "Available countries returned successfully."}},
)
async def get_available_countries(c: ContainerDep):
    events = await c.get_macro_events()

    use_case = GetAvailableCountriesUseCase()
    result = use_case.execute(events)

    return result
