from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Scalper Today API"
    app_version: str = "15.1.0"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    openrouter_api_key: str = Field(default="", description="OpenRouter API Key - REQUIRED")
    openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_model: str = "google/gemini-2.5-flash"

    http_timeout_seconds: float = 90.0
    forexfactory_calendar_url: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

    database_path: str = Field(
        default="data/scalper_today.db", description="Path to SQLite database"
    )

    refresh_api_key: str = Field(default="", description="API key for /macro/refresh endpoint")

    server_host: str = "127.0.0.1"
    server_port: int = 8000

    notification_check_interval: int = Field(
        default=60, description="Notification scheduler check interval in seconds"
    )
    notification_before_minutes: int = Field(
        default=5, description="Minutes before event to send notification"
    )

    @property
    def is_ai_configured(self) -> bool:
        return bool(self.openrouter_api_key and self.openrouter_api_key != "your_api_key_here")

    jwt_secret_key: str = Field(default="", description="JWT secret key for signing tokens")
    jwt_algorithm: str = "HS256"
    jwt_token_expire_days: int = 7

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed origins",
    )

    @property
    def is_auth_configured(self) -> bool:
        return bool(self.jwt_secret_key and self.jwt_secret_key != "")

    @property
    def cors_origins_list(self) -> list:
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
