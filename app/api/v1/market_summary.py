"""
app/api/v1/market_summary.py
==============================
Route handler for the market summary aggregate stats endpoint.

GET /api/v1/market-summary

Returns: avg PE, total companies, highest market cap, last updated.
All values are computed on read — not stored in the database.
"""

import logging

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_stock_service
from app.schemas.market_summary_schema import MarketSummaryResponse
from app.services.stock_service import StockService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=MarketSummaryResponse,
    summary="Get market summary",
    description=(
        "Returns aggregate statistics across all tracked companies (or a specific sector): "
        "total companies, average P/E ratio, highest market cap company, "
        "and the timestamp of the last data refresh. "
        "All values are computed on read — nothing is pre-aggregated or stored."
    ),
    status_code=status.HTTP_200_OK,
)
async def get_market_summary(
    sector: str | None = Query(None, description="Filter summary stats by sector"),
    service: StockService = Depends(get_stock_service),
) -> MarketSummaryResponse:
    return await service.get_market_summary(sector=sector)
