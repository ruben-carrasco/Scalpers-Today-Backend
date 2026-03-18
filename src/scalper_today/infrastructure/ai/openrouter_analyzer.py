import asyncio
import json
import logging
from typing import Dict, List

import httpx

from scalper_today.config import Settings
from scalper_today.domain import (
    AIAnalysis,
    BriefingStats,
    DailyBriefing,
    EconomicEvent,
    IAIAnalyzer,
)
from scalper_today.domain.exceptions import ExternalServiceError
from scalper_today.domain.usecases import CacheKeyGenerator, EventFilter

logger = logging.getLogger(__name__)


class OpenRouterAnalyzer(IAIAnalyzer):
    BATCH_SIZE = 10
    DEEP_BATCH_SIZE = 3

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._client = http_client
        self._key_gen = CacheKeyGenerator()

    @property
    def _is_configured(self) -> bool:
        return self._settings.is_ai_configured

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

    async def analyze_events(self, events: List[EconomicEvent]) -> Dict[str, AIAnalysis]:
        if not self._is_configured:
            logger.warning("AI not configured - OPENROUTER_API_KEY missing")
            return {}

        if not events:
            return {}

        try:
            results: Dict[str, AIAnalysis] = {}
            total_batches = (len(events) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

            logger.info(f"Starting quick analysis of {len(events)} events in {total_batches} batches")

            for batch_idx in range(0, len(events), self.BATCH_SIZE):
                batch = events[batch_idx : batch_idx + self.BATCH_SIZE]
                batch_num = (batch_idx // self.BATCH_SIZE) + 1

                logger.info(
                    f"Processing quick analysis batch {batch_num}/{total_batches} ({len(batch)} events)"
                )

                batch_results = await self._analyze_quick_batch(batch)
                results.update(batch_results)

            logger.info(f"Quick analysis complete: {len(results)}/{len(events)} events analyzed")
            return results
        except ExternalServiceError as e:
            logger.warning(f"AI analysis unavailable, returning empty results: {e.message}")
            return {}

    async def analyze_events_deep(self, events: List[EconomicEvent]) -> Dict[str, AIAnalysis]:
        if not self._is_configured:
            logger.warning("AI not configured for deep analysis")
            return {}

        high_impact = EventFilter.high_impact_only(events)

        if not high_impact:
            logger.info("No high-impact events for deep analysis")
            return {}

        try:
            results: Dict[str, AIAnalysis] = {}
            total_batches = (len(high_impact) + self.DEEP_BATCH_SIZE - 1) // self.DEEP_BATCH_SIZE

            logger.info(
                f"Starting deep analysis of {len(high_impact)} high-impact events in {total_batches} batches"
            )

            for batch_idx in range(0, len(high_impact), self.DEEP_BATCH_SIZE):
                batch = high_impact[batch_idx : batch_idx + self.DEEP_BATCH_SIZE]
                batch_num = (batch_idx // self.DEEP_BATCH_SIZE) + 1

                logger.info(
                    f"Processing deep analysis batch {batch_num}/{total_batches} ({len(batch)} events)"
                )

                batch_results = await self._analyze_deep_batch(batch)
                results.update(batch_results)

            logger.info(
                f"Deep analysis complete: {len(results)}/{len(high_impact)} high-impact events analyzed"
            )
            return results
        except ExternalServiceError as e:
            logger.warning(f"AI deep analysis unavailable, returning empty results: {e.message}")
            return {}

    async def _analyze_quick_batch(self, batch: List[EconomicEvent]) -> Dict[str, AIAnalysis]:
        prompt_data = [
            {
                "id": idx,
                "evento": e.title,
                "pais": e.country,
                "divisa": e.currency,
                "actual": e.actual,
                "prevision": e.forecast,
                "anterior": e.previous,
                "sorpresa": e.surprise,
                "estrellas": int(e.importance),
            }
            for idx, e in enumerate(batch)
        ]

        prompt = self._build_quick_analysis_prompt(prompt_data)
        response = await self._call_api(prompt, temperature=0.1, max_tokens=2000)

        if not response:
            return {}

        results: Dict[str, AIAnalysis] = {}
        for id_str, data in response.items():
            try:
                idx = int(id_str)
                if 0 <= idx < len(batch):
                    key = self._key_gen.for_event(batch[idx])
                    results[key] = self._dict_to_ai_analysis(data)
            except (ValueError, KeyError) as e:
                logger.debug(f"Failed to parse quick analysis result {id_str}: {e}")

        return results

    async def _analyze_deep_batch(self, batch: List[EconomicEvent]) -> Dict[str, AIAnalysis]:
        prompt_data = [
            {
                "id": idx,
                "evento": e.title,
                "pais": e.country,
                "divisa": e.currency,
                "actual": e.actual,
                "prevision": e.forecast,
                "anterior": e.previous,
                "sorpresa": e.surprise,
                "hora": e.time,
            }
            for idx, e in enumerate(batch)
        ]

        prompt = self._build_deep_analysis_prompt(prompt_data)
        response = await self._call_api(prompt, temperature=0.2, max_tokens=6000)

        if not response:
            return {}

        results: Dict[str, AIAnalysis] = {}
        for id_str, data in response.items():
            try:
                idx = int(id_str)
                if 0 <= idx < len(batch):
                    key = self._key_gen.for_event(batch[idx])
                    # Note: AI returns Spanish keys, we map to English
                    results[key] = AIAnalysis(
                        summary=data.get("resumen", ""),
                        impact=data.get("impacto", "HIGH"),
                        sentiment=data.get("sentimiento", "NEUTRAL"),
                        macro_context=data.get("contexto_macro", ""),
                        technical_levels=data.get("niveles_tecnicos", ""),
                        trading_strategies=data.get("estrategias_trading", ""),
                        impacted_assets=data.get("activos_impactados", ""),
                        is_deep_analysis=True,
                    )
            except (ValueError, KeyError) as e:
                logger.debug(f"Failed to parse deep analysis result {id_str}: {e}")

        return results

    async def generate_briefing(self, events: List[EconomicEvent]) -> DailyBriefing:
        if not self._is_configured:
            logger.warning("AI not configured for briefing")
            return DailyBriefing.empty_day(len(events))

        high_impact = EventFilter.high_impact_only(events)

        # Use high impact if available, otherwise fallback to top medium/all events to still have a briefing
        briefing_events = (
            high_impact if high_impact else [e for e in events if int(e.importance) >= 2]
        )
        if not briefing_events:
            briefing_events = events[:10]

        if not briefing_events:
            logger.info("No events for briefing")
            return DailyBriefing.empty_day(0)

        logger.info(
            f"Generating briefing from {len(briefing_events)} events (high impact: {len(high_impact)})"
        )

        summary_data = [
            {
                "hora": e.time,
                "evento": e.title,
                "pais": e.country,
                "importancia": int(e.importance),
                "actual": e.actual,
                "prevision": e.forecast,
                "anterior": e.previous,
                "sorpresa": e.surprise,
            }
            for e in briefing_events
        ]

        try:
            prompt = self._build_briefing_prompt(summary_data)
            response = await self._call_api(prompt, temperature=0.2, max_tokens=2000)

            if not response:
                return DailyBriefing.error("Error obteniendo respuesta de IA")

            briefing = self._dict_to_briefing(response)
            briefing.statistics.total_events_today = len(events)
            briefing.statistics.high_impact_count = len(high_impact)
            return briefing
        except ExternalServiceError as e:
            logger.warning(f"Briefing generation unavailable: {e.message}")
            return DailyBriefing.error("Servicio de IA temporalmente no disponible")
        except Exception as e:
            logger.error(f"Failed to parse briefing response: {e}")
            return DailyBriefing.error("Error parseando respuesta de IA")

    def _dict_to_ai_analysis(self, data: dict) -> AIAnalysis:
        return AIAnalysis(
            summary=data.get("resumen", data.get("summary", "N/A")),
            impact=data.get("impacto", data.get("impact", "N/A")),
            sentiment=data.get("sentimiento", data.get("sentiment", "NEUTRAL")),
            macro_context=data.get("contexto_macro", data.get("macro_context")),
            technical_levels=data.get("niveles_tecnicos", data.get("technical_levels")),
            trading_strategies=data.get("estrategias_trading", data.get("trading_strategies")),
            impacted_assets=data.get("activos_impactados", data.get("impacted_assets")),
        )

    def _dict_to_briefing(self, data: dict) -> DailyBriefing:
        stats_data = data.get("statistics", {})
        stats = BriefingStats(
            sentiment=stats_data.get("sentiment", "NEUTRAL"),
            volatility_level=stats_data.get("volatility_level", "LOW"),
        )

        return DailyBriefing(
            general_outlook=data.get("general_outlook", "N/A"),
            impacted_assets=data.get("impacted_assets", []),
            cautionary_hours=data.get("cautionary_hours", []),
            statistics=stats,
        )

    MAX_RETRIES = 2
    RETRY_BASE_DELAY = 1  # seconds

    async def _call_api(
        self, prompt: str, temperature: float = 0.1, max_tokens: int = 4000
    ) -> dict | None:
        last_exception = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await self._client.post(
                    self._settings.openrouter_url,
                    json={
                        "model": self._settings.openrouter_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    headers=self._headers,
                    timeout=self._settings.http_timeout_seconds,
                )

                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    return self._parse_json(content)

                # Don't retry client errors (4xx) except 429
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    logger.error(
                        f"OpenRouter client error {response.status_code}: {response.text[:200]}"
                    )
                    raise ExternalServiceError(
                        "OpenRouter",
                        f"API returned {response.status_code}",
                    )

                logger.warning(
                    f"OpenRouter error {response.status_code} "
                    f"(attempt {attempt}/{self.MAX_RETRIES})"
                )

            except ExternalServiceError:
                raise
            except httpx.TimeoutException as e:
                logger.warning(
                    f"OpenRouter API timeout (attempt {attempt}/{self.MAX_RETRIES})"
                )
                last_exception = e
            except KeyError as e:
                logger.error(f"Unexpected API response structure: {e}")
                raise ExternalServiceError("OpenRouter", f"Unexpected response: {e}")
            except Exception as e:
                logger.warning(
                    f"API call failed: {e} (attempt {attempt}/{self.MAX_RETRIES})"
                )
                last_exception = e

            if attempt < self.MAX_RETRIES:
                delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

        error_msg = f"OpenRouter failed after {self.MAX_RETRIES} attempts"
        if last_exception:
            error_msg += f": {last_exception}"
        raise ExternalServiceError("OpenRouter", error_msg)

    @staticmethod
    def _parse_json(content: str) -> dict | None:
        clean = content.strip()

        if clean.startswith("```"):
            lines = clean.split("\n")
            lines = lines[1:]
            clean = "\n".join(lines)

        if clean.endswith("```"):
            clean = clean[:-3]

        clean = clean.strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.debug(f"Raw content: {content[:500]}")
            return None

    @staticmethod
    def _build_quick_analysis_prompt(events_data: list) -> str:
        return f"""Actúa como analista financiero. Analiza estos datos macroeconómicos de forma RÁPIDA y CONCISA.

IMPORTANTE: Responde ÚNICAMENTE con JSON válido, sin texto adicional ni markdown.

Estructura requerida (por cada evento):
{{
  "0": {{"resumen": "Análisis en máximo 40 palabras", "impacto": "ALTO|MEDIO|BAJO", "sentimiento": "POSITIVO|NEGATIVO|NEUTRO"}},
  "1": {{...}}
}}

CAMPOS DE DATOS:
- "actual": dato publicado (vacío si aún no se ha publicado)
- "prevision": lo que esperaba el mercado
- "anterior": dato del periodo anterior
- "sorpresa": positive/negative/neutral (comparación actual vs previsión)

REGLA CRÍTICA SOBRE DATO ACTUAL:
- Si "actual" tiene valor: El dato YA se publicó. Analiza la SORPRESA (actual vs previsión). NO digas "sin datos actuales" ni "pendiente de publicación". Compara actual con previsión y anterior para determinar impacto real.
- Si "actual" está vacío: El dato aún no se ha publicado. Analiza expectativas basándote en previsión y anterior.

Criterios para IMPACTO (considera las estrellas como guía base):
- eventos 3★: Generalmente ALTO, salvo que el dato sea exactamente como se esperaba
- eventos 2★: Generalmente MEDIO, puede ser ALTO si hay gran sorpresa
- eventos 1★: Generalmente BAJO, puede ser MEDIO si hay sorpresa significativa

Criterios para RESUMEN:
- Con dato actual: Indica si superó/decepcionó expectativas y el impacto en el mercado
- Sin dato actual: Indica qué se espera y los escenarios posibles

Criterios para SENTIMIENTO:
- POSITIVO: bueno para la economía/fortalece el activo
- NEGATIVO: malo para la economía/debilita el activo
- NEUTRO: sin impacto claro o dato neutral

Datos:
{json.dumps(events_data, ensure_ascii=False)}"""

    @staticmethod
    def _build_deep_analysis_prompt(events_data: list) -> str:
        return f"""Actúa como Jefe de Estrategia de un Hedge Fund institucional.
Analiza estos eventos de ALTO IMPACTO con máxima profundidad para traders profesionales.

IMPORTANTE: Responde ÚNICAMENTE con JSON válido, sin texto adicional ni markdown.

DATOS DE EVENTOS DE ALTO IMPACTO (3 ESTRELLAS):
{json.dumps(events_data, ensure_ascii=False)}

REGLA CRÍTICA SOBRE DATO ACTUAL:
- Si "actual" tiene valor: El dato YA se publicó. Analiza el RESULTADO REAL: compara actual vs previsión y anterior. NO uses lenguaje condicional ("podría", "si el dato sale..."). Habla en pasado/presente sobre lo que ocurrió.
- Si "actual" está vacío: El dato aún no se ha publicado. Analiza expectativas y escenarios pre-dato.

DIRECTRICES PROFESIONALES:

1. CONTEXTO MONETARIO (2025/2026):
   - Enfócate en expectativas de recortes/mantenimiento, NO en subidas genéricas
   - Menciona cómo afecta el pricing de futuros de tipos (CME FedWatch si aplica)
   - Relaciona con última decisión de bancos centrales

2. JERARQUÍA EN DATOS MULTI-COMPONENTE:
   - NFP: Salarios (Average Hourly Earnings) > Desempleo > Headline
   - CPI: Core CPI > Headline CPI
   - GDP: Deflator > crecimiento headline
   - Indica EXPLÍCITAMENTE qué componente vigilar primero

3. NIVELES TÉCNICOS ESPECÍFICOS:
   - NO digas "resistencia fuerte", di "resistencia 1.0950 (máximo 20 días)"
   - Incluye stops concretos: "stop loss en 1.0880 (-25 pips)"
   - Menciona ATR actual o volatilidad implícita si relevante

4. TIMING Y SESIONES:
   - Pre-NY (sesión europea): posicionamiento cautious
   - Post-dato (sesión americana): ejecución direccional
   - Especifica ventanas de volatilidad (ej: "pico 14:30-15:30 EST")

ESTRUCTURA REQUERIDA (por cada evento):
{{
  "0": {{
    "resumen": "Análisis ejecutivo en 2-3 líneas. Indica: componente clave a vigilar, expectativa de mercado, y dirección más probable según sorpresa.",
    "impacto": "ALTO",
    "sentimiento": "Pre-dato: NEUTRO | Post-dato: POSITIVO/NEGATIVO según lectura",
    "contexto_macro": "100-150 palabras. Incluye: (1) tendencia reciente del indicador, (2) implicaciones para política monetaria (recortes/pausa), (3) efecto en crecimiento/inflación, (4) contexto vs datos anteriores, (5) expectativa de mercado (consenso) y rango histórico. Menciona si el mercado ya ha 'priced in' algún escenario.",
    "niveles_tecnicos": "80-100 palabras. Formato: 'ACTIVO | Resistencia: X (contexto) | Soporte: Y (contexto) | Rango esperado: Z pips/puntos | ATR: valor | Stop sugerido: nivel (-pips)'. Ejemplo: 'EUR/USD | R: 1.0950 (máximo 20d) | S: 1.0800 (mínimo mensual) | Rango: 80-120 pips post-dato | Stop compra: 1.0875 (-25 pips)'",
    "estrategias_trading": "80-100 palabras. FORMATO OBLIGATORIO: 'ESCENARIO 1 (dato fuerte/sorpresa al alza): Long/Short ACTIVO, entrada X, target Y, stop Z, timeframe (ej: intraday 14:30-16:00). ESCENARIO 2 (dato débil/decepción): estrategia inversa. GESTIÓN: tamaño posición (ej: 0.5% cuenta), ratio riesgo/beneficio mínimo 1:2'. Incluye plan pre-posicionamiento si aplica.",
    "activos_impactados": "Lista ordenada por volatilidad esperada con DIRECCIONES específicas: 'USD/JPY (↑ si NFP > 200k), EUR/USD (↓), S&P 500 (↓ si salarios altos por temor Fed hawkish), Gold (↓), US10Y yields (↑)'"
  }},
  "1": {{...}}
}}

EJEMPLOS DE LENGUAJE PROFESIONAL:

❌ "El dato podría afectar al EUR/USD"
✅ "EUR/USD bajo presión bajista si NFP > 210k, objetivo 1.0850 (-100 pips), stop 1.0975"

❌ "Importante vigilar la inflación"
✅ "Core CPI crítico: lectura > 0.3% MoM retrasaría recortes Q2 2025, pricing actual: 65% probabilidad recorte marzo"

❌ "Posible movimiento alcista"
✅ "Setup: Long S&P 500 en pullback 4850 si NFP débil, target 4920 (+70 pts), stop 4820, R/R 2.3:1"

ENFOQUE:
- Trader intraday con objetivo 0.5-1% diario
- Gestión estricta de riesgo (stops siempre)
- Decisiones basadas en precio + dato + contexto macro
- Lenguaje preciso tipo "prop firm evaluation"
"""

    @staticmethod
    def _build_briefing_prompt(events_data: list) -> str:
        return f"""Actúa como Jefe de Estrategia de un Hedge Fund institucional.
Genera un "Daily Briefing" profesional para traders profesionales.

IMPORTANTE: Responde ÚNICAMENTE con JSON válido, sin texto adicional ni markdown.

DATOS DE EVENTOS DE ALTO IMPACTO:
{json.dumps(events_data, ensure_ascii=False)}

REGLA CRÍTICA SOBRE DATO ACTUAL:
- Si "actual" tiene valor: El dato YA se publicó. Genera el briefing basándote en los RESULTADOS REALES. Compara actual vs previsión. NO uses lenguaje condicional ("podría", "si el dato sale..."). Habla sobre lo que ocurrió y su impacto real.
- Si "actual" está vacío: El dato aún no se ha publicado. Genera el briefing basándote en expectativas y escenarios pre-dato.

DIRECTRICES CRÍTICAS:

1. CONTEXTO MONETARIO ACTUAL (2025/2026):
   - NO uses "subidas de tipos" genéricas
   - Enfócate en: expectativas de recortes, mantenimiento o pausa de política monetaria
   - Menciona cómo el dato afecta las expectativas de la Fed/BCE/BoE

2. JERARQUÍA DE DATOS (para eventos multi-componente como NFP):
   - Indica qué componente es MÁS relevante para el mercado
   - Ej: En NFP → Salarios > Desempleo > Headline
   - Ej: En CPI → Core > Headline

3. TIMING PRE/POST DATO:
   - Pre-dato: Sentiment neutral / "wait & see"
   - Post-dato: Movimiento direccional esperado
   - Aclarar diferencia entre sesión europea y americana

4. ELIMINACIÓN DE RUIDO:
   - NO menciones "total_events_today" ni estadísticas irrelevantes para trading
   - SOLO enfócate en eventos de alto impacto y su operativa

ESTRUCTURA REQUERIDA:
{{
  "general_outlook": "Párrafo de 80-120 palabras. Incluye: (1) evento protagonista, (2) qué componente del dato es clave, (3) cómo afecta expectativas de política monetaria (recortes/pausa/mantenimiento), (4) contexto pre-dato vs post-dato, (5) nivel de volatilidad esperado con timeframe específico (ej: alta volatilidad post-14:30 en sesión americana).",
  "impacted_assets": ["Activos específicos con dirección esperada si aplica: 'USD/JPY (fortaleza USD si dato fuerte)', 'S&P 500 (presión bajista)', 'US10Y (subida yields)'"],
  "cautionary_hours": ["Hora exacta + evento + qué componente vigilar: '14:30 (NFP: priorizar Average Hourly Earnings)', '16:00 (Powell: guidance sobre recortes 2025)'"],
  "statistics": {{
    "sentiment": "Pre-dato: Neutral/Cautious | Post-dato: Risk-On/Risk-Off según resultado",
    "volatility_level": "Alta (especificar ventana temporal: ej. 14:30-16:00 EST)"
  }}
}}

EJEMPLOS DE LENGUAJE PROFESIONAL:
❌ "El dato podría influir en subidas de tipos"
✅ "El dato podría retrasar expectativas de recortes Q2 2025"

❌ "Volatilidad alta"
✅ "Volatilidad elevada esperada post-14:30 EST, con rango ampliado en S&P 500 (+/- 1.5%)"

❌ "Impacto en EUR/USD"
✅ "EUR/USD bajo presión si NFP supera 200k (objetivo 1.0850, soporte crítico 1.0800)"

ENFOQUE OPERATIVO:
- Piensa como trader intraday con objetivo 0.5-1% diario
- Prioriza niveles técnicos específicos y gestión de riesgo
- Indica pre-posicionamiento vs reacción post-dato"""
