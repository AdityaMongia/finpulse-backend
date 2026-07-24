"""
app/database/engine.py
======================
SQLAlchemy async engine creation.

This module is responsible for creating a single, shared, async SQLAlchemy
engine that is reused across all database operations in the application.

Why async?
----------
FastAPI is built on async I/O (via asyncio/Starlette).  Using a sync engine
would block the event loop during every DB call, negating the performance
benefit of async Python.  `asyncpg` is the fastest async PostgreSQL driver
available.

Connection Pooling:
-------------------
SQLAlchemy manages a connection pool automatically.  Key parameters:
  - pool_size:      Number of persistent connections kept alive
  - max_overflow:   Extra connections allowed when pool is exhausted
  - pool_timeout:   Seconds to wait for a connection before raising
  - pool_pre_ping:  Sends a lightweight "ping" before using a connection
                    to detect stale/broken connections silently

Usage:
    from app.database.engine import engine
    # Use indirectly via the session factory — don't use engine directly in routes.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)


def _build_engine() -> AsyncEngine:
    """
    Build the async SQLAlchemy engine from application settings.

    Returns a fully configured `AsyncEngine` instance.
    The engine is NOT a database connection — it is a factory for connections.
    """
    logger.debug(
        "Creating async database engine | pool_size=%d max_overflow=%d",
        settings.DATABASE_POOL_SIZE,
        settings.DATABASE_MAX_OVERFLOW,
    )

    return create_async_engine(
        url=settings.DATABASE_URL,
        # --- Connection pool ---
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,          # Detects dead connections automatically
        pool_recycle=3600,           # Recycle connections older than 1 hour
        # --- Debugging ---
        echo=settings.DEBUG,         # Log all SQL statements in DEBUG mode
        echo_pool=settings.DEBUG,    # Log pool checkout/checkin events
        # --- Async driver ---
        # asyncpg is configured via the URL scheme: postgresql+asyncpg://
    )


# Module-level singleton engine.
# Imported by session.py and by Alembic's env.py.
engine: AsyncEngine = _build_engine()
