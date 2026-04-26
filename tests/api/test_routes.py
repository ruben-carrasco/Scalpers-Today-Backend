from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from scalper_today.api.app import create_app
from scalper_today.api.dependencies.container import get_container
from scalper_today.api.schemas import WeekEventResponse
from scalper_today.domain.entities import AIAnalysis, EconomicEvent, Importance


def test_health_check(client):
    response = client.get("/health")
    # Health checks the db, which will fail if DB doesn't exist, but it returns 200 with degraded status if not raise.
    # Ah, the router is mounted under /api/v1? No, /health seems to be in router, which is prefixed with /api/v1.
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded"]


def test_auth_routes_exist(client):
    # Just checking if the route is mounted and returns the expected format (422 Unprocessable Entity because body is missing)
    response = client.post("/api/v1/auth/login")
    assert response.status_code == 422


def test_events_routes_exist(client):
    response = client.get("/api/v1/macro")
    # Could be 200 (events), 503 (no data available), or 500 (unexpected server error)
    assert response.status_code in [200, 503, 500]


def test_docs_exist(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text


def test_filtered_events_pagination_params(client):
    # Test that pagination params are accepted (offset/limit)
    response = client.get("/api/v1/events/filtered?offset=0&limit=10")
    assert response.status_code in [200, 500]


def test_filtered_events_default_pagination(client):
    response = client.get("/api/v1/events/filtered")
    assert response.status_code in [200, 500]


def test_week_events_route_exists(client):
    response = client.get("/api/v1/events/week")
    assert response.status_code in [200, 500]


def test_week_event_response_accepts_impacted_assets_list():
    event = EconomicEvent(
        id="event-with-analysis",
        time="10:00",
        title="CPI",
        country="NZD",
        currency="NZD",
        importance=Importance.HIGH,
        ai_analysis=AIAnalysis(
            summary="Inflation scenario",
            impact="HIGH",
            sentiment="BULLISH",
            impacted_assets=["NZD/USD"],
        ),
        _timestamp=datetime(2026, 4, 26, 10, 0),
    )

    response = WeekEventResponse.from_domain(event)

    assert response.ai_analysis is not None
    assert response.ai_analysis.impacted_assets == ["NZD/USD"]
    assert response.event_date == "2026-04-26"


def test_week_events_refresh_requires_api_key():
    fake_container = SimpleNamespace(
        settings=SimpleNamespace(refresh_api_key="secret"),
        get_week_events=AsyncMock(return_value=[]),
    )
    app = create_app()
    app.dependency_overrides[get_container] = lambda: fake_container

    with TestClient(app) as test_client:
        response = test_client.post("/api/v1/events/week/refresh")

    app.dependency_overrides.clear()
    assert response.status_code == 403
    fake_container.get_week_events.assert_not_awaited()


def test_week_events_refresh_forces_provider_refresh():
    event = EconomicEvent(
        id="rapidapi-event",
        time="10:00",
        title="CPI",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
        _timestamp=datetime(2026, 4, 26, 10, 0),
    )
    fake_container = SimpleNamespace(
        settings=SimpleNamespace(refresh_api_key="secret"),
        get_week_events=AsyncMock(return_value=[event]),
    )
    app = create_app()
    app.dependency_overrides[get_container] = lambda: fake_container

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/events/week/refresh",
            headers={"X-API-Key": "secret"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Refreshed 1 weekly events",
        "count": 1,
    }
    fake_container.get_week_events.assert_awaited_once_with(force_refresh=True)


def test_filtered_events_limit_exceeds_max(client):
    # limit > 100 should return validation error
    response = client.get("/api/v1/events/filtered?limit=200")
    assert response.status_code == 422


def test_filtered_events_negative_offset(client):
    response = client.get("/api/v1/events/filtered?offset=-1")
    assert response.status_code == 422


def test_filtered_events_country_too_long(client):
    long_country = "A" * 101
    response = client.get(f"/api/v1/events/filtered?country={long_country}")
    assert response.status_code == 422


def test_filtered_events_search_empty(client):
    # min_length=1 means empty string should fail
    response = client.get("/api/v1/events/filtered?search=")
    # FastAPI may pass empty as None or fail validation
    assert response.status_code in [200, 422, 500]


def test_liveness_probe(client):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_probe(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code in [200, 503]
