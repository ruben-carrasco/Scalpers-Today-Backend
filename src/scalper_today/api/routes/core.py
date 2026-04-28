import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from scalper_today.api.dependencies import Container, get_container
from ..schemas import ErrorResponse, HealthCheckResponse, StatusResponse, ReadinessResponse

logger = logging.getLogger(__name__)
router = APIRouter()

ContainerDep = Annotated[Container, Depends(get_container)]


@router.get(
    "/health",
    tags=["System"],
    summary="Service health overview",
    description=(
        "Returns the API version, deployment environment, database status, and AI configuration "
        "status. Intended for dashboards and manual diagnostics."
    ),
    response_model=HealthCheckResponse,
    responses={200: {"description": "Health status returned successfully."}},
)
async def health_check(c: ContainerDep) -> HealthCheckResponse:
    database_status = "unknown"
    ai_service_status = "configured" if c.settings.is_ai_configured else "not_configured"

    try:
        async with c.database_manager.session() as session:
            await session.execute(text("SELECT 1"))
            database_status = "healthy"
    except Exception as e:
        database_status = "unhealthy"
        logger.error(f"Database health check failed: {e}")

    return HealthCheckResponse(
        status="healthy" if database_status == "healthy" else "degraded",
        version=c.settings.app_version,
        environment=c.settings.app_env,
        checks={
            "database": database_status,
            "ai_service": ai_service_status,
        },
    )


@router.get(
    "/health/live",
    tags=["System"],
    summary="Liveness probe",
    description="Lightweight probe that confirms the process is running.",
    response_model=StatusResponse,
    responses={200: {"description": "Application process is alive."}},
)
async def liveness_probe() -> StatusResponse:
    return StatusResponse(status="alive")


@router.get(
    "/health/ready",
    tags=["System"],
    summary="Readiness probe",
    description="Checks whether required dependencies are ready to serve traffic.",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "Application is ready to serve traffic."},
        503: {"model": ErrorResponse, "description": "A required dependency is not ready."},
    },
)
async def readiness_probe(c: ContainerDep) -> ReadinessResponse:
    is_ready = True
    checks = {}

    try:
        async with c.database_manager.session() as session:
            await session.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception:
        checks["database"] = False
        is_ready = False

    checks["ai_configured"] = c.settings.is_ai_configured

    status = "ready" if is_ready else "not_ready"

    if not is_ready:
        raise HTTPException(status_code=503, detail={"status": status, "checks": checks})

    return ReadinessResponse(status=status, checks=checks)
