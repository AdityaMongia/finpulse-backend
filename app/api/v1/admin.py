"""
app/api/v1/admin.py
====================
Admin/maintenance endpoints for manually triggering scheduler jobs.

These are development/ops endpoints — not exposed to end users.
They allow manual triggering of data refresh jobs without waiting for
the scheduled time (e.g., after a server restart that missed the 4:30 PM job).
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.scheduler.jobs import refresh_historical, refresh_fundamentals, refresh_live_prices

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/refresh/historical",
    summary="Manually trigger historical OHLCV refresh",
    tags=["Admin"],
)
async def trigger_refresh_historical(background_tasks: BackgroundTasks) -> dict:
    """
    Manually trigger today's historical OHLCV refresh for all tracked companies.

    Use this when:
    - The server was restarted after 4:30 PM IST and missed today's scheduled job
    - You want to force-fetch today's closing data immediately

    Runs in the background — returns immediately with a 202 Accepted response.
    Check server logs for progress.
    """
    logger.info("[Admin] Manual historical refresh triggered via API")
    background_tasks.add_task(refresh_historical)
    return {
        "status": "accepted",
        "message": "Historical refresh job started in background. Check server logs for progress.",
        "job": "refresh_historical",
    }


@router.post(
    "/refresh/live-prices",
    summary="Manually trigger live price refresh",
    tags=["Admin"],
)
async def trigger_refresh_live_prices(background_tasks: BackgroundTasks) -> dict:
    """
    Manually trigger a live price + volume refresh for all tracked companies.
    """
    logger.info("[Admin] Manual live price refresh triggered via API")
    background_tasks.add_task(refresh_live_prices)
    return {
        "status": "accepted",
        "message": "Live price refresh job started in background.",
        "job": "refresh_live_prices",
    }


@router.post(
    "/refresh/fundamentals",
    summary="Manually trigger fundamentals refresh",
    tags=["Admin"],
)
async def trigger_refresh_fundamentals(background_tasks: BackgroundTasks) -> dict:
    """
    Manually trigger PE, EPS, market cap, 52w-range refresh for all companies.
    """
    logger.info("[Admin] Manual fundamentals refresh triggered via API")
    background_tasks.add_task(refresh_fundamentals)
    return {
        "status": "accepted",
        "message": "Fundamentals refresh job started in background.",
        "job": "refresh_fundamentals",
    }


@router.post(
    "/refresh/all",
    summary="Trigger ALL refresh jobs at once",
    tags=["Admin"],
)
async def trigger_refresh_all(background_tasks: BackgroundTasks) -> dict:
    """
    Run live prices, fundamentals, and historical refresh back-to-back.
    Use after a server restart to bring all data up to date.
    """
    logger.info("[Admin] Manual FULL refresh triggered via API")
    background_tasks.add_task(refresh_live_prices)
    background_tasks.add_task(refresh_fundamentals)
    background_tasks.add_task(refresh_historical)
    return {
        "status": "accepted",
        "message": "All 3 refresh jobs started in background (live prices → fundamentals → historical).",
        "jobs": ["refresh_live_prices", "refresh_fundamentals", "refresh_historical"],
    }
