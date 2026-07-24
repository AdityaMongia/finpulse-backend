"""
app/database/session.py
========================
Async session factory and FastAPI dependency for database session management.

Concepts
--------
AsyncSession:
    A SQLAlchemy session that executes queries asynchronously.
    It acts as a unit-of-work: collects operations and flushes them
    together.  Always use as an async context manager or via `get_db`.

AsyncSessionLocal:
    A session factory.  Calling `AsyncSessionLocal()` creates a new
    session bound to the shared engine.

get_db:
    An async generator dependency for FastAPI's `Depends()` system.
    It yields a session, then commits or rolls back + closes after the
    route handler finishes.

Usage (in route handlers):
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.database.session import get_db

    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(SomeModel))
        ...
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.engine import engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Attributes remain accessible after commit
                             # (important for returning Pydantic models after INSERT)
    autocommit=False,        # Always explicit — commit only when everything succeeds
    autoflush=False,         # Flush manually or rely on commit
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async generator that yields a database session for use inside a request.

    Lifecycle:
      1. A new session is created at the start of each request.
      2. The session is yielded to the route handler.
      3. If the handler completes without error → commit.
      4. If an exception is raised → rollback.
      5. The session is always closed at the end (via finally).

    This dependency is injected using FastAPI's `Depends()`:
        async def my_route(db: AsyncSession = Depends(get_db)): ...

    The session is NOT shared between requests — each request gets its own.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Database session rolled back due to exception")
            raise
        finally:
            await session.close()
