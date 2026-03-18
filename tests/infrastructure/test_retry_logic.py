import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from scalper_today.config import Settings
from scalper_today.infrastructure.scrapers.investing_scraper import InvestingComScraper
from scalper_today.infrastructure.ai.openrouter_analyzer import OpenRouterAnalyzer
from scalper_today.domain.exceptions import ExternalServiceError


def make_settings(**overrides):
    defaults = dict(
        openrouter_api_key="test-key",
        openrouter_url="https://api.test.com/chat",
        openrouter_model="test-model",
        http_timeout_seconds=10.0,
        investing_api_url="https://investing.test.com/api",
    )
    defaults.update(overrides)
    return MagicMock(spec=Settings, **defaults, is_ai_configured=True)


def make_response(status_code=200, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data or {}
    return resp


# ── InvestingComScraper Retry ───────────────────────


class TestScraperRetry:
    @pytest.fixture
    def settings(self):
        return make_settings()

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self, settings):
        client = AsyncMock()
        client.post.side_effect = [
            httpx.TimeoutException("timeout"),
            httpx.TimeoutException("timeout"),
            make_response(200, json_data={"data": "<html></html>"}),
        ]
        scraper = InvestingComScraper(settings, client)

        with patch("scalper_today.infrastructure.scrapers.investing_scraper.asyncio.sleep", new_callable=AsyncMock):
            result = await scraper._fetch_calendar_html()

        assert result == "<html></html>"
        assert client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_on_client_error(self, settings):
        client = AsyncMock()
        client.post.return_value = make_response(400)
        scraper = InvestingComScraper(settings, client)

        with patch("scalper_today.infrastructure.scrapers.investing_scraper.asyncio.sleep", new_callable=AsyncMock):
            result = await scraper._fetch_calendar_html()

        assert result == ""
        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_500(self, settings):
        client = AsyncMock()
        client.post.side_effect = [
            make_response(500, text="Internal Error"),
            make_response(200, json_data={"data": "<table></table>"}),
        ]
        scraper = InvestingComScraper(settings, client)

        with patch("scalper_today.infrastructure.scrapers.investing_scraper.asyncio.sleep", new_callable=AsyncMock):
            result = await scraper._fetch_calendar_html()

        assert result == "<table></table>"
        assert client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_empty_after_max_retries(self, settings):
        client = AsyncMock()
        client.post.side_effect = httpx.TimeoutException("timeout")
        scraper = InvestingComScraper(settings, client)

        with patch("scalper_today.infrastructure.scrapers.investing_scraper.asyncio.sleep", new_callable=AsyncMock):
            result = await scraper._fetch_calendar_html()

        assert result == ""
        assert client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_retries_on_429(self, settings):
        client = AsyncMock()
        client.post.side_effect = [
            make_response(429, text="Rate limited"),
            make_response(200, json_data={"data": "<ok></ok>"}),
        ]
        scraper = InvestingComScraper(settings, client)

        with patch("scalper_today.infrastructure.scrapers.investing_scraper.asyncio.sleep", new_callable=AsyncMock):
            result = await scraper._fetch_calendar_html()

        assert result == "<ok></ok>"
        assert client.post.call_count == 2


# ── OpenRouterAnalyzer Retry ────────────────────────


class TestAnalyzerRetry:
    @pytest.fixture
    def settings(self):
        return make_settings()

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self, settings):
        client = AsyncMock()
        client.post.side_effect = [
            httpx.TimeoutException("timeout"),
            make_response(200, json_data={
                "choices": [{"message": {"content": '{"0": {"resumen": "ok"}}'}}]
            }),
        ]
        analyzer = OpenRouterAnalyzer(settings, client)

        with patch("scalper_today.infrastructure.ai.openrouter_analyzer.asyncio.sleep", new_callable=AsyncMock):
            result = await analyzer._call_api("test prompt")

        assert result == {"0": {"resumen": "ok"}}
        assert client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self, settings):
        client = AsyncMock()
        client.post.side_effect = httpx.TimeoutException("timeout")
        analyzer = OpenRouterAnalyzer(settings, client)

        with patch("scalper_today.infrastructure.ai.openrouter_analyzer.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ExternalServiceError):
                await analyzer._call_api("test prompt")

        assert client.post.call_count == 2  # MAX_RETRIES = 2

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, settings):
        client = AsyncMock()
        client.post.return_value = make_response(401, text="Unauthorized")
        analyzer = OpenRouterAnalyzer(settings, client)

        with patch("scalper_today.infrastructure.ai.openrouter_analyzer.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ExternalServiceError):
                await analyzer._call_api("test prompt")

        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_500(self, settings):
        client = AsyncMock()
        client.post.side_effect = [
            make_response(500, text="Server Error"),
            make_response(200, json_data={
                "choices": [{"message": {"content": '{"result": "ok"}'}}]
            }),
        ]
        analyzer = OpenRouterAnalyzer(settings, client)

        with patch("scalper_today.infrastructure.ai.openrouter_analyzer.asyncio.sleep", new_callable=AsyncMock):
            result = await analyzer._call_api("test prompt")

        assert result == {"result": "ok"}
        assert client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_bad_request(self, settings):
        client = AsyncMock()
        client.post.return_value = make_response(400, text="Bad Request")
        analyzer = OpenRouterAnalyzer(settings, client)

        with patch("scalper_today.infrastructure.ai.openrouter_analyzer.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ExternalServiceError):
                await analyzer._call_api("test prompt")

        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_analyze_events_returns_empty_on_service_error(self, settings):
        client = AsyncMock()
        client.post.side_effect = httpx.TimeoutException("timeout")
        analyzer = OpenRouterAnalyzer(settings, client)

        from scalper_today.domain.entities import EconomicEvent, Importance

        events = [EconomicEvent(
            id="1", time="10:00", title="Test",
            country="US", currency="USD", importance=Importance.HIGH,
        )]

        with patch("scalper_today.infrastructure.ai.openrouter_analyzer.asyncio.sleep", new_callable=AsyncMock):
            result = await analyzer.analyze_events(events)

        assert result == {}

    @pytest.mark.asyncio
    async def test_generate_briefing_returns_fallback_on_service_error(self, settings):
        client = AsyncMock()
        client.post.side_effect = httpx.TimeoutException("timeout")
        analyzer = OpenRouterAnalyzer(settings, client)

        from scalper_today.domain.entities import EconomicEvent, Importance

        events = [EconomicEvent(
            id="1", time="10:00", title="Test",
            country="US", currency="USD", importance=Importance.HIGH,
        )]

        with patch("scalper_today.infrastructure.ai.openrouter_analyzer.asyncio.sleep", new_callable=AsyncMock):
            result = await analyzer.generate_briefing(events)

        assert result is not None
        assert "no disponible" in result.general_outlook.lower() or "error" in result.general_outlook.lower()
