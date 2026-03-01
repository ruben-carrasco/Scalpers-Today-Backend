import pytest
from unittest.mock import AsyncMock, MagicMock
from scalper_today.infrastructure.ai.openrouter_analyzer import OpenRouterAnalyzer
from scalper_today.domain.entities import EconomicEvent
from scalper_today.domain.entities import Importance


@pytest.fixture
def analyzer(mock_ai_analyzer):
    from scalper_today.config import get_settings
    import httpx
    import os

    # Mock the API key in environment so analyzer thinks it is configured
    os.environ["OPENROUTER_API_KEY"] = "test_key"
    settings = get_settings()
    return OpenRouterAnalyzer(settings, httpx.AsyncClient())


@pytest.mark.asyncio
async def test_analyze_events_empty(analyzer):
    results = await analyzer.analyze_events([])
    assert results == {}


@pytest.mark.asyncio
async def test_openrouter_parsing_logic(analyzer):
    # We mock the http client inside the analyzer
    analyzer._client = AsyncMock()

    # Force _is_configured logic to pass by patching the settings
    analyzer._settings.openrouter_api_key = "test_key"

    from scalper_today.domain.usecases import CacheKeyGenerator

    event = EconomicEvent(
        id="event_1",
        time="10:00",
        title="Test Event",
        country="US",
        currency="USD",
        importance=Importance.HIGH,
    )
    key = CacheKeyGenerator.for_event(event)

    mock_response = MagicMock()
    mock_response.status_code = 200
    # The backend expects keys to be the INDEX in the batch (as string), e.g. "0"
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"0": {"resumen": "Test Summary", "impacto": "HIGH", "sentimiento": "BULLISH"}}'
                }
            }
        ]
    }
    analyzer._client.post.return_value = mock_response

    results = await analyzer.analyze_events([event])

    assert len(results) == 1
    assert key in results
    assert results[key].sentiment == "BULLISH"
    assert results[key].impact == "HIGH"
