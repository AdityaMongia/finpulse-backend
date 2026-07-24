"""
app/config.py
=============
Centralised application configuration powered by pydantic-settings.

All settings are loaded from environment variables (with optional .env file
fallback).  Every setting is strongly typed, so mis-configurations are caught
at startup, not at runtime.

Usage:
    from app.config import settings

    db_url = settings.DATABASE_URL
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings resolved from environment variables.

    pydantic-settings reads values from (in priority order):
      1. Actual environment variables
      2. .env file (specified by env_file below)
      3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # APP_NAME == app_name
        extra="ignore",        # Ignore unknown env vars gracefully
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "FinPulse"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8005

    # ------------------------------------------------------------------
    # Database
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    # ------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/finpulse_db",
        description="Async PostgreSQL connection URL",
    )
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    SECRET_KEY: str = Field(
        default="change-this-in-production",
        description="Secret key used for JWT signing and other crypto",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_TIMEZONE: str = "Asia/Kolkata"

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ORIGINS: list[str] = [
        "http://localhost:3005",
        "http://localhost:5173",
    ]

    # ------------------------------------------------------------------
    # Derived / computed helpers
    # ------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """True when running in a production environment."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """True when running in development mode."""
        return self.APP_ENV == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.

    Using @lru_cache means the .env file is only read once at startup,
    not on every call.  This also makes it easy to override in tests:

        app.config.get_settings.cache_clear()
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    """
    return Settings()


# Convenience module-level alias
# Import this anywhere in the codebase:  from app.config import settings
settings: Settings = get_settings()
