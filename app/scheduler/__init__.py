"""
app/scheduler/__init__.py
==========================
APScheduler background job scheduler package.

The scheduler runs periodic jobs independently of incoming HTTP requests.
It is started in the FastAPI `lifespan` context (main.py) and stopped
gracefully on application shutdown.

Planned jobs (to be added in Phase 2):
  - refresh_all_market_data()   → Every 15 minutes during market hours
  - fetch_historical_prices()   → Once daily after market close
  - cleanup_old_data()          → Weekly cleanup of stale records
"""
