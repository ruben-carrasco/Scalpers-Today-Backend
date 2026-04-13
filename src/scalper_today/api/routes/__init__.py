from .core import router as core_router
from .events import router as events_router
from . import auth, alerts

# Backward-compatible alias for previous imports from scalper_today.api.routes import router
router = events_router

__all__ = ["core_router", "events_router", "router", "auth", "alerts"]
