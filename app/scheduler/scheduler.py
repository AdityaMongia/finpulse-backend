"""
app/scheduler/scheduler.py
===========================
APScheduler AsyncIOScheduler factory with all three jobs wired.

Jobs per Section 7:
  - refresh_live_prices  → every 3 minutes
  - refresh_fundamentals → daily at 08:00 IST
  - refresh_historical   → daily at 16:30 IST (after NSE close)

The scheduler singleton is started in main.py lifespan and stopped on shutdown.
"""

import logging
from functools import lru_cache

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)


def _build_scheduler() -> AsyncIOScheduler:
    """
    Build and configure the APScheduler AsyncIOScheduler with all jobs.
    """
    job_defaults = {
        "coalesce": True,           # Don't stack missed runs
        "max_instances": 1,         # One concurrent instance per job
        "misfire_grace_time": 300,  # Allow jobs to fire up to 5 min late
    }

    scheduler = AsyncIOScheduler(
        jobstores={"default": MemoryJobStore()},
        executors={"default": AsyncIOExecutor()},
        job_defaults=job_defaults,
        timezone=settings.SCHEDULER_TIMEZONE,
    )

    # Import jobs here (inside function) to avoid circular imports at module load
    from app.scheduler.jobs import (
        refresh_fundamentals,
        refresh_historical,
        refresh_live_prices,
    )

    # --- Job 1: Live prices — every 3 minutes ---
    scheduler.add_job(
        func=refresh_live_prices,
        trigger="interval",
        minutes=3,
        id="refresh_live_prices",
        name="Refresh live prices (every 3 min)",
        replace_existing=True,
    )
    logger.debug("Registered job: refresh_live_prices (interval=3min)")

    # --- Job 2: Fundamentals — daily at 08:00 IST ---
    scheduler.add_job(
        func=refresh_fundamentals,
        trigger="cron",
        hour=8,
        minute=0,
        id="refresh_fundamentals",
        name="Refresh fundamentals (daily 08:00 IST)",
        replace_existing=True,
    )
    logger.debug("Registered job: refresh_fundamentals (cron 08:00)")

    # --- Job 3: Historical prices — daily at 16:30 IST (after NSE close) ---
    scheduler.add_job(
        func=refresh_historical,
        trigger="cron",
        hour=16,
        minute=30,
        id="refresh_historical",
        name="Refresh historical OHLCV (daily 16:30 IST)",
        replace_existing=True,
    )
    logger.debug("Registered job: refresh_historical (cron 16:30)")

    logger.info(
        "APScheduler configured with %d jobs | timezone=%s",
        len(scheduler.get_jobs()),
        settings.SCHEDULER_TIMEZONE,
    )
    return scheduler


@lru_cache(maxsize=1)
def get_scheduler() -> AsyncIOScheduler:
    """
    Return the cached singleton scheduler instance.
    Always returns the same object — safe to call from anywhere.
    """
    return _build_scheduler()
