"""
app/api/router.py
==================
Master API router that aggregates all versioned sub-routers.

Final URL structure:
    GET  /api/v1/stocks/                   → list all stocks
    GET  /api/v1/stocks/{ticker}           → single stock detail
    POST /api/v1/stocks/                   → register new ticker
    GET  /api/v1/historical/{ticker}       → OHLCV history (?range=1m/3m/6m/1y)
    GET  /api/v1/market-summary/           → aggregate stats
    GET  /api/v1/compare/                  → multi-stock comparison
    GET  /api/v1/search/                   → fuzzy search by name/ticker
"""

from fastapi import APIRouter

from app.api.v1 import compare, historical, market_summary, search, stocks

api_router = APIRouter()

api_router.include_router(
    stocks.router,
    prefix="/v1/stocks",
    tags=["Stocks"],
)
api_router.include_router(
    historical.router,
    prefix="/v1/historical",
    tags=["Historical Prices"],
)
api_router.include_router(
    market_summary.router,
    prefix="/v1/market-summary",
    tags=["Market Summary"],
)
api_router.include_router(
    compare.router,
    prefix="/v1/compare",
    tags=["Comparison"],
)
api_router.include_router(
    search.router,
    prefix="/v1/search",
    tags=["Search"],
)
