import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from scalper_today.api.dependencies import init_container
from scalper_today.config import get_settings
from .routes.core import router as core_router
from .routes.events import router as events_router
from .exception_handlers import register_exception_handlers

logger = logging.getLogger(__name__)

API_KEY_PROTECTED_PATHS = {
    "/api/v1/macro/refresh",
    "/api/v1/events/week/refresh",
    "/api/v1/events/analysis/backfill",
}
JWT_PROTECTED_PATHS = {
    "/api/v1/auth/me",
}


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("🚀 Starting ScalperToday API...")

    async with init_container() as container:
        app.state.container = container
        logger.info("✅ Ready to serve requests")
        yield

    logger.info("👋 Shutdown complete")


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # Define security schemes used by the API.
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        },
    }

    for path, methods in openapi_schema["paths"].items():
        for method in methods:
            operation = openapi_schema["paths"][path][method]

            # Explicit API key protected operations.
            if path in API_KEY_PROTECTED_PATHS:
                operation["security"] = [{"ApiKeyAuth": []}]
                continue

            # JWT-protected operations.
            if path in JWT_PROTECTED_PATHS or path.startswith("/api/v1/alerts"):
                operation["security"] = [{"BearerAuth": []}]
                continue

            # Public operation: ensure no lock icon
            operation.pop("security", None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    settings = get_settings()

    tags_metadata = [
        {
            "name": "System",
            "description": "Health checks used by Azure, uptime monitors, and deployment probes.",
        },
        {
            "name": "Authentication",
            "description": "Public login/register endpoints and the JWT-protected current-user endpoint.",
        },
        {
            "name": "Events",
            "description": "Public macroeconomic calendar data normalized for the application.",
        },
        {
            "name": "Briefing",
            "description": "AI-generated daily market context derived from economic events.",
        },
        {
            "name": "Mobile - Home",
            "description": "Aggregated payloads optimized for the mobile home screen.",
        },
        {
            "name": "Mobile - Events",
            "description": "Event lists, filters, date ranges, and mobile calendar views.",
        },
        {
            "name": "Mobile - Config",
            "description": "Configuration data consumed by the mobile application.",
        },
        {
            "name": "Admin - Refresh",
            "description": "Manual cache refresh and AI maintenance endpoints. Requires the `X-API-Key` header.",
        },
        {
            "name": "Alerts",
            "description": "JWT-protected user alerts and push notification device tokens.",
        },
    ]

    app = FastAPI(
        title="ScalperToday API",
        description=(
            "Backend API for the ScalperToday mobile app.\n\n"
            "It normalizes economic calendar data from external providers, stores a short-lived "
            "cache, exposes AI-generated market context, and manages user alerts.\n\n"
            "Authentication uses JWT Bearer tokens for user resources. Manual refresh operations "
            "use the `X-API-Key` header and are shown with a separate Swagger lock."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=tags_metadata,
        swagger_ui_parameters={
            "docExpansion": "list",
            "filter": True,
            "displayRequestDuration": True,
        },
    )

    # Set custom openapi schema
    app.openapi = lambda: custom_openapi(app)

    cors_origins = settings.cors_origins_list

    if not cors_origins:
        cors_origins = ["http://localhost:3000", "http://localhost:8080", "http://localhost:19006"]
        logger.info(f"CORS: Using default origins for {settings.app_env}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-API-Key"],
    )

    app.include_router(core_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")

    from .routes import auth, alerts

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(alerts.router, prefix="/api/v1")

    register_exception_handlers(app)

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": f"{settings.app_name} v{settings.app_version} - Production Ready",
            "docs": "/docs",
        }

    return app


app = create_app()
