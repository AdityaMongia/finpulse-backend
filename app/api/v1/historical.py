"""
app/api/v1/historical.py
=========================
Route handler for historical OHLCV price data.

GET /api/v1/historical/{ticker}?range=3m

?range options: 1m (default) | 3m | 6m | 1y
Returns empty prices array with HTTP 200 if no data exists — per error spec.
"""

import logging

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_stock_service
from app.schemas.historical_schema import HistoricalPriceResponse
from app.services.stock_service import StockService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{ticker}",
    response_model=HistoricalPriceResponse,
    summary="Get historical OHLCV prices",
    description=(
        "Returns daily Open/High/Low/Close/Volume data for the specified ticker "
        "over the requested date range. "
        "Use ?range=1m (default), 3m, 6m, or 1y. "
        "Returns an empty prices array (HTTP 200) if no historical data exists yet."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Ticker not found in the tracking database"},
        422: {"description": "Invalid range parameter"},
    },
)
async def get_historical_prices(
    ticker: str,
    range: str = Query(
        default="1m",
        description="Date range: 1m = 1 month, 3m = 3 months, 6m = 6 months, 1y = 1 year",
        examples=["3m"],
    ),
    service: StockService = Depends(get_stock_service),
) -> HistoricalPriceResponse:
    return await service.get_historical_prices(ticker=ticker, range_param=range)
