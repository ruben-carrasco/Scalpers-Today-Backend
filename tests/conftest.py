import os

# Add the src folder to Python path before importing application modules
import sys
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi.testclient import TestClient

from scalper_today.api.app import app
from scalper_today.api.routes.events import _reset_refresh_rate_limit


@pytest.fixture(autouse=True)
def reset_rate_limit():
    _reset_refresh_rate_limit()
    yield


@pytest.fixture
def client():
    # Use TestClient as a context manager to trigger the app lifespan events
    # This is crucial because it initializes the Container.
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_event_repository():
    repo = AsyncMock()
    # By default, mock the get_events method to return an empty list
    repo.get_events.return_value = []
    return repo


@pytest.fixture
def mock_ai_analyzer():
    analyzer = AsyncMock()
    return analyzer
