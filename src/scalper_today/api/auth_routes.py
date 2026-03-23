import logging
import time
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .schemas import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserResponse,
    TokenResponse,
    ErrorResponse,
    UserPreferencesResponse,
)
from scalper_today.domain.usecases import (
    RegisterUserUseCase,
    RegisterUserRequest as RegisterUserReq,
    LoginUserUseCase,
    LoginUserRequest as LoginUserReq,
    GetCurrentUserUseCase,
)
from scalper_today.api.dependencies import Container, get_container
from scalper_today.domain.entities import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

# Dependency type aliases
ContainerDep = Annotated[Container, Depends(get_container)]
TokenDep = Annotated[HTTPAuthorizationCredentials, Depends(security)]

# --- Rate Limiting ---
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX_ATTEMPTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60


def _check_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = _rate_limit_store[client_ip]

    # Remove attempts outside the window
    _rate_limit_store[client_ip] = [t for t in attempts if now - t < RATE_LIMIT_WINDOW_SECONDS]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_ATTEMPTS:
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    _rate_limit_store[client_ip].append(now)


def _map_user_to_response(user) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        preferences=UserPreferencesResponse(
            language=user.preferences.language.value,
            currency=user.preferences.currency.value,
            timezone=user.preferences.timezone.value,
        ),
        is_verified=user.is_verified,
    )


def _map_token_to_response(token) -> TokenResponse:
    return TokenResponse(
        access_token=token.access_token, token_type=token.token_type, expires_in=token.expires_in
    )


async def get_current_user_dep(
    credentials: TokenDep,
    container: ContainerDep,
):
    token = credentials.credentials

    async with container.database_manager.session() as session:
        user_repo = container.get_user_repository(session)
        jwt_service = container.get_jwt_service()
        use_case = GetCurrentUserUseCase(user_repo, jwt_service)

        user = await use_case.execute(token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User registered successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        409: {"model": ErrorResponse, "description": "Email already exists"},
    },
    summary="Register new user",
    description="Create a new user account with email and password",
)
async def register(request: RegisterRequest, container: ContainerDep, req: Request):
    _check_rate_limit(req)
    async with container.database_manager.session() as session:
        user_repo = container.get_user_repository(session)
        jwt_service = container.get_jwt_service()
        use_case = RegisterUserUseCase(user_repo, jwt_service)

        use_case_request = RegisterUserReq(
            email=request.email,
            password=request.password,
            name=request.name,
            language=request.language,
            currency=request.currency,
            timezone=request.timezone,
        )

        result = await use_case.execute(use_case_request)

        return AuthResponse(
            user=_map_user_to_response(result.user), token=_map_token_to_response(result.token)
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Login successful"},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        403: {"model": ErrorResponse, "description": "Account disabled"},
    },
    summary="Login user",
    description="Authenticate with email and password, receive JWT token",
)
async def login(request: LoginRequest, container: ContainerDep, req: Request):
    _check_rate_limit(req)
    async with container.database_manager.session() as session:
        user_repo = container.get_user_repository(session)
        jwt_service = container.get_jwt_service()
        use_case = LoginUserUseCase(user_repo, jwt_service)

        use_case_request = LoginUserReq(email=request.email, password=request.password)

        result = await use_case.execute(use_case_request)

        return AuthResponse(
            user=_map_user_to_response(result.user), token=_map_token_to_response(result.token)
        )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Current user data"},
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
    },
    summary="Get current user",
    description="Get authenticated user's profile information",
)
async def get_me(current_user: Annotated[User, Depends(get_current_user_dep)]) -> UserResponse:
    return _map_user_to_response(current_user)
