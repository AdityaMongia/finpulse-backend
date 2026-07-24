"""
app/api/v1/summary.py
======================
Route handlers for stock summary / dashboard endpoints.

Registered under: /api/v1/summary/

Planned endpoints:
  GET /api/v1/summary/{ticker}
      → Full dashboard summary for a single stock:
          - Company info (sector, industry, exchange)
          - Current market data (price, PE, market cap, volume)
          - 52-week high/low
          - Recent price change % (1d, 1w, 1m, 3m, 1y)
          - Dividend yield

Design note:
  The summary endpoint aggregates data from multiple sources (companies +
  market_data + historical_prices) into a single response. This aggregation
  is done entirely in the service layer to keep this route thin.
"""

import logging

from fastapi import APIRouter, Depends, status

from app.api.deps import get_stock_service
from app.services.stock_service import StockService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{ticker}",
    summary="Get stock dashboard summary",
    description=(
        "Returns a complete dashboard summary for a single stock, including "
        "company details, live price, key metrics, and price change percentages."
    ),
    status_code=status.HTTP_200_OK,
)
async def get_stock_summary(
    ticker: str,
    service: StockService = Depends(get_stock_service),
) -> dict:
    """
    TODO: Implement using StockService.get_summary(ticker)
    Will return: StockSummaryResponse (to be defined in schemas)
    Will raise: NotFoundError if ticker does not exist
    """
    return {"message": f"Not yet implemented — ticker={ticker}"}
