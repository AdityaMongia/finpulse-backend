"""
app/api/deps.py
================
Shared FastAPI dependency callables.

Dependencies defined here are reusable across ALL route handlers via
FastAPI's `Depends()` system.  This is the standard FastAPI pattern for
dependency injection.

How Depends() works:
  1. FastAPI introspects the function signature of the route handler.
  2. For each parameter typed as `Depends(some_function)`, FastAPI calls
     `some_function` and injects the return value.
  3. If the dependency is an async generator (like `get_db`), FastAPI manages
     the lifecycle: it runs the generator up to `yield`, injects the yielded
     value, and then resumes the generator (for cleanup) after the response.

Usage in a route handler:
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.api.deps import get_db, get_stock_service

    @router.get("/stocks")
    async def list_stocks(
        db: AsyncSession = Depends(get_db),
        service: StockService = Depends(get_stock_service),
    ): ...
"""

import logging
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services.comparison_service import ComparisonService
from app.services.stock_service import StockService

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Re-export get_db so route files only need to import from app.api.deps
# ------------------------------------------------------------------------------

# get_db is already defined in app.database.session
# Re-export it here so routes import from a single place.
__all__ = ["get_db"]


# ------------------------------------------------------------------------------
# Service factory dependencies
# ------------------------------------------------------------------------------

async def get_stock_service(
    db: AsyncSession = Depends(get_db),
) -> StockService:
    """
    Factory dependency that creates a StockService for the current request.

    The database session is injected by FastAPI from the `get_db` dependency,
    then passed to the service constructor.

    Usage:
        @router.get("/stocks")
        async def route(service: StockService = Depends(get_stock_service)):
            ...
    """
    return StockService(db=db)


async def get_comparison_service(
    db: AsyncSession = Depends(get_db),
) -> ComparisonService:
    """
    Factory dependency that creates a ComparisonService for the current request.
    """
    return ComparisonService(db=db)


# ------------------------------------------------------------------------------
# Auth dependency stubs (to be implemented when auth is added)
# ------------------------------------------------------------------------------

async def get_current_user():
    """
    Stub dependency — returns None until authentication is implemented.

    Future implementation will:
      1. Extract the Bearer token from the Authorization header
      2. Decode and verify the JWT using SECRET_KEY from settings
      3. Look up the user in the database
      4. Return the user object (or raise UnauthorizedError)
    """
    # TODO: Implement JWT authentication
    return None
