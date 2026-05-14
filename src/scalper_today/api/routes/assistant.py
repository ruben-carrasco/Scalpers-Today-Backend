import logging
import time
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from scalper_today.api.dependencies import Container, get_container
from scalper_today.api.routes.auth import get_current_user_dep
from scalper_today.domain.exceptions import ExternalServiceError

from ..schemas import AssistantChatRequest, AssistantChatResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Assistant"])

ContainerDep = Annotated[Container, Depends(get_container)]

_assistant_rate_limit_store: dict[str, list[float]] = defaultdict(list)
ASSISTANT_RATE_LIMIT_MAX_ATTEMPTS = 20
ASSISTANT_RATE_LIMIT_WINDOW_SECONDS = 60


def _check_assistant_rate_limit(request: Request, user_id: str) -> None:
    key = f"{user_id}:{request.url.path}"
    now = time.monotonic()
    attempts = _assistant_rate_limit_store[key]
    _assistant_rate_limit_store[key] = [
        t for t in attempts if now - t < ASSISTANT_RATE_LIMIT_WINDOW_SECONDS
    ]

    if len(_assistant_rate_limit_store[key]) >= ASSISTANT_RATE_LIMIT_MAX_ATTEMPTS:
        logger.warning("Assistant rate limit exceeded", extra={"user_id": user_id})
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas preguntas. Intenta de nuevo en unos segundos.",
        )

    _assistant_rate_limit_store[key].append(now)


def _reset_assistant_rate_limit() -> None:
    _assistant_rate_limit_store.clear()


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the educational AI assistant",
    description=(
        "JWT-protected assistant for educational explanations about macroeconomic concepts, "
        "calendar events, app data, and AI analysis. It must not provide personalized "
        "financial advice or direct buy/sell signals."
    ),
    responses={
        200: {"description": "Assistant answer returned successfully."},
        401: {"model": ErrorResponse, "description": "Invalid or expired token."},
        429: {"model": ErrorResponse, "description": "Too many assistant requests."},
        503: {"model": ErrorResponse, "description": "AI service unavailable."},
    },
)
async def chat_with_assistant(
    request: AssistantChatRequest,
    req: Request,
    container: ContainerDep,
    current_user=Depends(get_current_user_dep),
) -> AssistantChatResponse:
    _check_assistant_rate_limit(req, current_user.id)

    try:
        context = request.context.model_dump() if request.context else None
        answer = await container.analyzer.generate_assistant_response(
            question=request.question.strip(),
            context=context,
        )
        return AssistantChatResponse(answer=answer)
    except ExternalServiceError as exc:
        logger.warning("Assistant unavailable", extra={"service": exc.service})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El asistente de IA no está disponible temporalmente.",
        ) from exc
