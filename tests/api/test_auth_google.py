import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from scalper_today.api.app import create_app
from scalper_today.api.dependencies import get_container


@pytest.fixture
def fake_container():
    container = MagicMock()
    # Mock JWT and User Repo
    container.get_jwt_service = MagicMock()
    container.get_user_repository = MagicMock()
    container.settings = MagicMock(google_client_id="test-google-id")
    container.database_manager.session.return_value.__aenter__.return_value = AsyncMock()
    return container


@pytest.fixture
def client(fake_container):
    app = create_app()
    app.dependency_overrides[get_container] = lambda: fake_container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_google_login_invalid_token(client):
    with patch(
        "google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Invalid token")
    ):
        response = client.post("/api/v1/auth/google", json={"id_token": "fake-token"})
        assert response.status_code == 401
        assert "Invalid Google token" in response.json()["detail"]["message"]
