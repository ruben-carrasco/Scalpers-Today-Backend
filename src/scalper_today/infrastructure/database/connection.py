"""Backward-compatible alias for database manager module."""

from .database_manager import DatabaseManager, get_db_session, get_db_url

__all__ = ["DatabaseManager", "get_db_session", "get_db_url"]
