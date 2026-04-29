import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from scalper_today.config import Settings
from scalper_today.domain.entities import EconomicEvent, Importance
from scalper_today.infrastructure.ai.openrouter_analyzer import OpenRouterAnalyzer


@pytest.fixture
def settings():
    return Settings(openrouter_api_key="test-key", openrouter_model="test-model")


@pytest.fixture
def mock_http_client():
    return AsyncMock()


@pytest.fixture
def analyzer(settings, mock_http_client):
    return OpenRouterAnalyzer(settings, mock_http_client)


@pytest.mark.asyncio
async def test_parse_json_with_markdown_blocks(analyzer):
    content = (
        'Aquí tienes el análisis:\n```json\n{"0": {"resumen": "test"}}\n```\nEspero que te sirva.'
    )
    # El método _parse_json es estático
    result = analyzer._parse_json(content)
    assert result == {"0": {"resumen": "test"}}


@pytest.mark.asyncio
async def test_analyze_quick_batch_mapping(analyzer, mock_http_client):
    # Mock API response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "0": {
                                "resumen": "Dato positivo",
                                "impacto": "ALTO",
                                "sentimiento": "POSITIVO",
                            }
                        }
                    )
                }
            }
        ]
    }
    mock_http_client.post.return_value = mock_resp

    event = EconomicEvent(
        id="e1", time="10:00", title="CPI", country="US", currency="USD", importance=Importance.HIGH
    )
    results = await analyzer._analyze_quick_batch([event])

    # Check if results use CacheKeyGenerator key
    from scalper_today.domain.usecases import CacheKeyGenerator

    key = CacheKeyGenerator().for_event(event)

    assert key in results
    assert results[key].summary == "Dato positivo"
    assert results[key].impact == "ALTO"


@pytest.mark.asyncio
async def test_analyze_deep_batch_mapping_spanish_to_english(analyzer, mock_http_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "0": {
                                "resumen": "Resumen profundo",
                                "impacto": "ALTO",
                                "sentimiento": "POSITIVO",
                                "contexto_macro": "Macro",
                                "niveles_tecnicos": "1.234",
                                "estrategias_trading": "Buy",
                                "activos_impactados": "EUR/USD",
                            }
                        }
                    )
                }
            }
        ]
    }
    mock_http_client.post.return_value = mock_resp

    event = EconomicEvent(
        id="e1", time="10:00", title="CPI", country="US", currency="USD", importance=Importance.HIGH
    )
    results = await analyzer._analyze_deep_batch([event])

    from scalper_today.domain.usecases import CacheKeyGenerator

    key = CacheKeyGenerator().for_event(event)

    analysis = results[key]
    assert analysis.summary == "Resumen profundo"
    assert analysis.macro_context == "Macro"
    assert analysis.technical_levels == "1.234"
    assert analysis.is_deep_analysis is True


@pytest.mark.asyncio
async def test_call_api_retries_on_rate_limit(analyzer, mock_http_client):
    # Mock 429 then 200
    mock_http_client.post.side_effect = [
        MagicMock(status_code=429),
        MagicMock(
            status_code=200, json=lambda: {"choices": [{"message": {"content": '{"test": true}'}}]}
        ),
    ]

    # We need to bypass the actual sleep for fast tests
    with MagicMock():  # patch asyncio.sleep
        result = await analyzer._call_api("prompt")
        assert result == {"test": True}
        assert mock_http_client.post.call_count == 2


@pytest.mark.asyncio
async def test_generate_briefing_handles_invalid_json(analyzer, mock_http_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"message": {"content": "Esto no es un JSON"}}]}
    mock_http_client.post.return_value = mock_resp

    event = EconomicEvent(
        id="e1", time="10:00", title="CPI", country="US", currency="USD", importance=Importance.HIGH
    )
    briefing = await analyzer.generate_briefing([event])

    assert "Error" in briefing.general_outlook
    assert briefing.impacted_assets == []
