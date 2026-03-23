import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from scalper_today.api.dependencies import init_container
from scalper_today.config import get_settings
from .routes import router
from .exception_handlers import register_exception_handlers

logger = logging.getLogger(__name__)


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
    )

    # Define the security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    # Public paths that should NOT have a lock icon
    public_paths = [
        "/login",
        "/register",
        "/health",
        "/live",
        "/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    for path, methods in openapi_schema["paths"].items():
        # Check if this path should be public
        is_public = any(pub in path for pub in public_paths)

        if not is_public:
            for method in methods:
                openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
        else:
            for method in methods:
                # Ensure public methods have no security defined
                if "security" in openapi_schema["paths"][path][method]:
                    del openapi_schema["paths"][path][method]["security"]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    settings = get_settings()

    tags_metadata = [
        {"name": "Authentication", "description": "User registration and login operations."},
        {"name": "Events", "description": "Economic calendar and macro data."},
        {
            "name": "Mobile - Home",
            "description": "Dashboard and daily briefing for the mobile app.",
        },
        {"name": "Mobile - Events", "description": "Filtering and upcoming event lists."},
        {"name": "Alerts", "description": "Custom user alerts and push notification tokens."},
        {"name": "System", "description": "Health checks and operational endpoints."},
    ]

    app = FastAPI(
        title="ScalperToday API",
        description=(
            "### 📈 Professional Financial News & AI Analysis\n\n"
            "This API powers the ScalperToday mobile application, providing real-time "
            "economic data enriched with institutional-grade AI analysis.\n\n"
            "**Core Capabilities:**\n"
            "* **AI Briefing**: Daily market outlook based on high-impact events.\n"
            "* **Sentiment Analysis**: Automatic bullish/bearish detection.\n"
            "* **Push Alerts**: Real-time notifications before market-moving news.\n"
            "* **Clean Architecture**: Built for stability and institutional scaling."
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
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    app.include_router(router, prefix="/api/v1")

    from . import auth_routes, alert_routes

    app.include_router(auth_routes.router, prefix="/api/v1")
    app.include_router(alert_routes.router, prefix="/api/v1")

    register_exception_handlers(app)

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": f"{settings.app_name} v{settings.app_version} - Production Ready",
            "docs": "/docs",
        }

    return app


app = create_app()
