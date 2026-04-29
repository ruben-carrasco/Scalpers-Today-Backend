import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
from datetime import date, timedelta
from fastapi.testclient import TestClient
from scalper_today.api.app import create_app
from scalper_today.api.dependencies import get_container

@pytest.fixture
def fake_container():
    container = MagicMock()
    container.settings = SimpleNamespace(refresh_api_key="secret-key")
    # Mocking necessary methods for different tests
    container.backfill_event_analysis = AsyncMock()
    container.refresh_macro_events = AsyncMock(return_value=[])
    container.get_week_events = AsyncMock(return_value=[])
    
    # Mock for home summary
    mock_summary = MagicMock()
    mock_summary.greeting = "Hola"
    mock_summary.date_formatted = "Hoy"
    mock_summary.time_formatted = "12:00"
    mock_summary.total_events = 5
    mock_summary.high_impact_count = 2
    mock_summary.medium_impact_count = 2
    mock_summary.low_impact_count = 1
    mock_summary.next_event = None
    mock_summary.sentiment = "BULLISH"
    mock_summary.volatility_level = "LOW"
    mock_summary.highlights = []
    container.get_home_summary = AsyncMock(return_value=mock_summary)
    
    container.get_macro_events = AsyncMock(return_value=[])
    
    return container

@pytest.fixture
def app_with_mock_container(fake_container):
    app = create_app()
    app.dependency_overrides[get_container] = lambda: fake_container
    yield app
    app.dependency_overrides.clear()

@pytest.fixture
def client(app_with_mock_container):
    with TestClient(app_with_mock_container) as test_client:
        yield test_client

# --- TESTS PARA /events/analysis/backfill ---

def test_backfill_invalid_api_key(client):
    response = client.post(
        "/api/v1/events/analysis/backfill",
        headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 403

def test_backfill_invalid_date_range_missing_one(client):
    response = client.post(
        "/api/v1/events/analysis/backfill?startDate=2026-04-20",
        headers={"X-API-Key": "secret-key"}
    )
    assert response.status_code == 422

def test_backfill_range_too_large(client):
    start = date(2026, 4, 1)
    end = start + timedelta(days=32)
    response = client.post(
        f"/api/v1/events/analysis/backfill?startDate={start}&endDate={end}",
        headers={"X-API-Key": "secret-key"}
    )
    assert response.status_code == 422

def test_backfill_rate_limit(client):
    for _ in range(10):
        client.post("/api/v1/events/analysis/backfill", headers={"X-API-Key": "secret-key"})
    
    response = client.post("/api/v1/events/analysis/backfill", headers={"X-API-Key": "secret-key"})
    assert response.status_code == 429

# --- TESTS PARA /events/week/refresh ---

def test_week_refresh_invalid_date_order(client):
    response = client.post(
        "/api/v1/events/week/refresh?startDate=2026-04-25&endDate=2026-04-20",
        headers={"X-API-Key": "secret-key"}
    )
    assert response.status_code == 422
    assert "greater than or equal to startDate" in response.json()["detail"]

def test_week_refresh_range_too_large(client):
    start = date(2026, 4, 1)
    end = start + timedelta(days=32)
    response = client.post(
        f"/api/v1/events/week/refresh?startDate={start}&endDate={end}",
        headers={"X-API-Key": "secret-key"}
    )
    assert response.status_code == 422
    assert "Date range cannot exceed" in response.json()["detail"]

def test_week_refresh_rate_limit(client):
    # El rate limit es por path
    for _ in range(10):
        client.post("/api/v1/events/week/refresh", headers={"X-API-Key": "secret-key"})
    
    response = client.post("/api/v1/events/week/refresh", headers={"X-API-Key": "secret-key"})
    assert response.status_code == 429

# --- TESTS PARA OTROS ENDPOINTS ---

def test_get_home_summary_structure(client, fake_container):
    response = client.get("/api/v1/home/summary")
    assert response.status_code == 200
    data = response.json()
    assert "welcome" in data
    assert "today_stats" in data
    assert "market_sentiment" in data
    assert data["today_stats"]["total_events"] == 5
    assert data["market_sentiment"]["overall"] == "BULLISH"

def test_get_events_by_importance_invalid(client):
    # Path parameter validation ge=1, le=3
    response = client.get("/api/v1/events/by-importance/4")
    assert response.status_code == 422 # FastAPI Query/Path validation returns 422

def test_get_events_by_importance_valid(client, fake_container):
    response = client.get("/api/v1/events/by-importance/3")
    assert response.status_code == 200
    fake_container.get_macro_events.assert_called_once()
