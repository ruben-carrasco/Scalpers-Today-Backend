import logging
from typing import Any

import httpx

from scalper_today.domain.dtos.notifications.notification_result import NotificationResult

from .expo_push_message import ExpoPushMessage

logger = logging.getLogger(__name__)


class ExpoPushService:
    EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client

    def _is_expo_token(self, token: str) -> bool:
        return token.startswith("ExponentPushToken[") or token.startswith("ExpoPushToken[")

    async def send_notification(
        self, tokens: list[str], title: str, body: str, data: dict[str, Any] | None = None
    ) -> NotificationResult:
        if not tokens:
            logger.warning("No tokens provided for notification")
            return NotificationResult(success_count=0, failure_count=0)

        # Filter valid Expo tokens
        valid_tokens = [t for t in tokens if self._is_expo_token(t)]
        invalid_count = len(tokens) - len(valid_tokens)

        if invalid_count > 0:
            logger.warning(f"Filtered out {invalid_count} invalid tokens (not Expo format)")

        if not valid_tokens:
            logger.warning("No valid Expo tokens to send to")
            return NotificationResult(success_count=0, failure_count=len(tokens))

        # Create messages for each token
        messages = [
            ExpoPushMessage(to=token, title=title, body=body, data=data).to_dict()
            for token in valid_tokens
        ]

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
        }

        try:
            response = await self.http_client.post(
                self.EXPO_PUSH_URL, json=messages, headers=headers, timeout=30.0
            )

            result_data = response.json()

            # Count successes and failures
            success_count = 0
            failure_count = 0

            if "data" in result_data:
                for item in result_data["data"]:
                    if item.get("status") == "ok":
                        success_count += 1
                    else:
                        failure_count += 1
                        error_msg = item.get("message", "Unknown error")
                        logger.warning(f"Push notification failed: {error_msg}")

            logger.info(f"Expo Push: {success_count} success, {failure_count} failures")

            return NotificationResult(
                success_count=success_count,
                failure_count=failure_count + invalid_count,
                results=result_data.get("data", []),
            )

        except httpx.HTTPError as e:
            logger.error(f"Expo Push request failed: {e}")
            return NotificationResult(success_count=0, failure_count=len(tokens), error=str(e))
        except Exception as e:
            logger.error(f"Unexpected error sending Expo Push: {e}")
            return NotificationResult(success_count=0, failure_count=len(tokens), error=str(e))

    async def send_event_alert(
        self,
        tokens: list[str],
        event_name: str,
        importance: int,
        country: str,
        currency: str = None,
        scheduled_time: str = None,
        actual: str = None,
    ) -> NotificationResult:
        # Choose emoji based on importance
        importance_emoji = "🔴" if importance >= 3 else "🟡" if importance == 2 else "🟢"

        # Build title
        title = f"{importance_emoji} {country}"
        if currency:
            title += f" ({currency})"

        # Build body
        if actual:
            body = f"{event_name}: {actual}"
        elif scheduled_time:
            body = f"{event_name} - {scheduled_time}"
        else:
            body = event_name

        data = {
            "type": "economic_event",
            "importance": str(importance),
            "country": country,
            "currency": currency or "",
            "event_name": event_name,
        }

        return await self.send_notification(tokens=tokens, title=title, body=body, data=data)

    async def send_daily_briefing(
        self, tokens: list[str], sentiment: str, high_impact_count: int
    ) -> NotificationResult:
        title = "📊 Resumen del Mercado"
        body = f"Hoy hay {high_impact_count} eventos de alto impacto. Sentimiento: {sentiment}"

        data = {
            "type": "daily_briefing",
            "sentiment": sentiment,
            "high_impact_count": str(high_impact_count),
        }

        return await self.send_notification(tokens=tokens, title=title, body=body, data=data)
