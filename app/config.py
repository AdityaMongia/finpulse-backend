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
from typing import Any, Literal

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
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/finpulse_db",
        description="Async PostgreSQL connection URL",
    )
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str | None) -> str:
        if isinstance(v, str):
            import re
            if v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            v = v.replace("sslmode=require", "ssl=require")
            v = re.sub(r"[?&]channel_binding=[^&]+", "", v)
            return v
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/finpulse_db"

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
        "https://finpulse-frontend-main.vercel.app",
        "https://finpulse-frontend.vercel.app",
        "*",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            if v.startswith("["):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

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
