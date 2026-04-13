import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

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
