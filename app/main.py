"""
app/main.py
===========
FastAPI application factory.

This is the entry point for the ASGI server:
    uvicorn app.main:app --reload

Responsibilities:
- Create the FastAPI application instance
- Register all routers
- Register exception handlers
- Register middleware (CORS, request logger)
- Define lifespan: startup & shutdown hooks
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.api.router import api_router
from app.middleware.request_logger import RequestLoggerMiddleware
from app.scheduler.scheduler import get_scheduler

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Lifespan context manager (replaces deprecated @app.on_event)
# ------------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Handle application startup and shutdown lifecycle.

    Everything BEFORE `yield` runs at startup.
    Everything AFTER `yield` runs at shutdown.

    FastAPI guarantees this runs even if startup raises an exception
    (Python's contextlib behaviour), so teardown is always attempted.
    """
    # ---- STARTUP --------------------------------------------------------
    logger.info(
        "Starting %s v%s [env=%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV,
    )

    configure_logging(level=settings.LOG_LEVEL, fmt=settings.LOG_FORMAT)

    # Start APScheduler if enabled
    if settings.SCHEDULER_ENABLED:
        scheduler = get_scheduler()
        scheduler.start()
        logger.info("APScheduler started")

    logger.info("Application startup complete ✓")

    yield  # Application is running here

    # ---- SHUTDOWN -------------------------------------------------------
    logger.info("Shutting down %s ...", settings.APP_NAME)

    if settings.SCHEDULER_ENABLED:
        scheduler = get_scheduler()
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("APScheduler stopped")

    logger.info("Application shutdown complete ✓")


# ------------------------------------------------------------------------------
# Application factory
# ------------------------------------------------------------------------------

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Separating app creation into a factory function makes it easy to:
    - Spin up multiple instances with different configs (e.g., testing)
    - Test the app without starting the server
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "FinPulse — Real-time Stock Market Monitoring Platform. "
            "Provides live quotes, historical prices, sector comparisons, "
            "and fundamental data for NSE/BSE listed companies."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # -- Middleware (order matters: outermost wraps innermost) ---------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggerMiddleware)

    # -- Exception handlers --------------------------------------------------
    register_exception_handlers(app)

    # -- Routers -------------------------------------------------------------
    app.include_router(api_router, prefix="/api")

    # -- Health check (outside versioned prefix) -----------------------------
    @app.get("/health", tags=["Health"], summary="Health check")
    async def health_check() -> dict:
        """
        Returns the application's operational status.
        Used by load balancers and monitoring tools.
        """
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        }

    return app


# Module-level app instance consumed by uvicorn
app: FastAPI = create_app()
