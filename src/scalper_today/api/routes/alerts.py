import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from scalper_today.api.dependencies import Container, get_container
from scalper_today.domain.entities import User
from scalper_today.domain.usecases import (
    CreateAlertRequest as CreateAlertReq,
)
from scalper_today.domain.usecases import (
    CreateAlertUseCase,
    DeleteAlertUseCase,
    ListUserAlertsUseCase,
    RegisterDeviceTokenUseCase,
    UpdateAlertUseCase,
)
from scalper_today.domain.usecases import (
    RegisterDeviceTokenRequest as RegisterDeviceReq,
)
from scalper_today.domain.usecases import (
    UpdateAlertRequest as UpdateAlertReq,
)

from ..schemas import (
    AlertConditionSchema,
    AlertResponse,
    CreateAlertRequest,
    DeviceTokenResponse,
    ErrorResponse,
    RegisterDeviceTokenRequest,
    UpdateAlertRequest,
)
from .auth import get_current_user_dep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])

# Dependency type aliases
ContainerDep = Annotated[Container, Depends(get_container)]
CurrentUserDep = Annotated[User, Depends(get_current_user_dep)]


def _map_alert_to_response(alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        name=alert.name,
        description=alert.description,
        conditions=[
            AlertConditionSchema(alert_type=c.alert_type.value, value=c.value)
            for c in alert.conditions
        ],
        status=alert.status.value,
        push_enabled=alert.push_enabled,
        trigger_count=alert.trigger_count,
        last_triggered_at=alert.last_triggered_at.isoformat() if alert.last_triggered_at else None,
        created_at=alert.created_at.isoformat(),
        updated_at=alert.updated_at.isoformat(),
    )


def _map_device_token_to_response(token) -> DeviceTokenResponse:
    return DeviceTokenResponse(
        id=token.id,
        device_type=token.device_type,
        device_name=token.device_name,
        is_active=token.is_active,
        created_at=token.created_at.isoformat(),
        last_used_at=token.last_used_at.isoformat(),
    )


@router.post(
    "/",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Alert created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="Create Alert",
    description="Create a new alert for the authenticated user",
)
async def create_alert(
    request: CreateAlertRequest,
    current_user: CurrentUserDep,
    container: ContainerDep,
):
    async with container.database_manager.session() as session:
        alert_repo = container.get_alert_repository(session)
        use_case = CreateAlertUseCase(alert_repo)

        use_case_request = CreateAlertReq(
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            conditions=[c.model_dump() for c in request.conditions],
            push_enabled=request.push_enabled,
        )

        result = await use_case.execute(use_case_request)

        return _map_alert_to_response(result)


@router.get(
    "/",
    response_model=list[AlertResponse],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "List of user alerts"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="List Alerts",
    description="Get all alerts for the authenticated user",
)
async def list_alerts(
    current_user: CurrentUserDep,
    container: ContainerDep,
    include_deleted: bool = False,
):
    async with container.database_manager.session() as session:
        alert_repo = container.get_alert_repository(session)
        use_case = ListUserAlertsUseCase(alert_repo)

        alerts = await use_case.execute(current_user.id, include_deleted=include_deleted)

        return [_map_alert_to_response(alert) for alert in alerts]


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Alert details"},
        404: {"model": ErrorResponse, "description": "Alert not found"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="Get Alert",
    description="Get a specific alert by ID",
)
async def get_alert(
    alert_id: str,
    current_user: CurrentUserDep,
    container: ContainerDep,
):
    async with container.database_manager.session() as session:
        alert_repo = container.get_alert_repository(session)
        alert = await alert_repo.get_by_id(alert_id)

        if not alert:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

        # Check ownership
        if alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this alert",
            )

        return _map_alert_to_response(alert)


@router.put(
    "/{alert_id}",
    response_model=AlertResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Alert updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        404: {"model": ErrorResponse, "description": "Alert not found"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="Update Alert",
    description="Update an existing alert",
)
async def update_alert(
    alert_id: str,
    request: UpdateAlertRequest,
    current_user: CurrentUserDep,
    container: ContainerDep,
):
    async with container.database_manager.session() as session:
        alert_repo = container.get_alert_repository(session)
        use_case = UpdateAlertUseCase(alert_repo)

        use_case_request = UpdateAlertReq(
            alert_id=alert_id,
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            conditions=[c.model_dump() for c in request.conditions] if request.conditions else None,
            status=request.status,
            push_enabled=request.push_enabled,
        )

        result = await use_case.execute(use_case_request)

        return _map_alert_to_response(result)


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Alert deleted successfully"},
        404: {"model": ErrorResponse, "description": "Alert not found"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="Delete Alert",
    description="Delete an alert (soft delete by default)",
)
async def delete_alert(
    alert_id: str,
    current_user: CurrentUserDep,
    container: ContainerDep,
    hard_delete: bool = False,
):
    async with container.database_manager.session() as session:
        alert_repo = container.get_alert_repository(session)
        use_case = DeleteAlertUseCase(alert_repo)

        success = await use_case.execute(
            alert_id=alert_id, user_id=current_user.id, soft_delete=not hard_delete
        )

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

        return None


@router.post(
    "/device-token",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Device token registered successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="Register Device Token",
    description="Register a device token for push notifications",
)
async def register_device_token(
    request: RegisterDeviceTokenRequest,
    current_user: CurrentUserDep,
    container: ContainerDep,
):
    async with container.database_manager.session() as session:
        device_repo = container.get_device_token_repository(session)
        use_case = RegisterDeviceTokenUseCase(device_repo)

        use_case_request = RegisterDeviceReq(
            user_id=current_user.id,
            token=request.token,
            device_type=request.device_type,
            device_name=request.device_name,
        )

        result = await use_case.execute(use_case_request)

        return _map_device_token_to_response(result)


@router.get(
    "/device-tokens",
    response_model=list[DeviceTokenResponse],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "List of user device tokens"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="List Device Tokens",
    description="Get all device tokens for the authenticated user",
)
async def list_device_tokens(
    current_user: CurrentUserDep,
    container: ContainerDep,
    active_only: bool = True,
):
    async with container.database_manager.session() as session:
        device_repo = container.get_device_token_repository(session)
        tokens = await device_repo.get_by_user_id(current_user.id, active_only=active_only)

        return [_map_device_token_to_response(token) for token in tokens]
