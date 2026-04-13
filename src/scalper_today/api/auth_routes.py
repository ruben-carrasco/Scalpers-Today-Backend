"""Backward-compatible import path for authentication routes."""

from .routes.auth import get_current_user_dep, router

__all__ = ["router", "get_current_user_dep"]
