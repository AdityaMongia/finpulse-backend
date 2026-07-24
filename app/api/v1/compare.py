"""
app/api/v1/compare.py
======================
Route handler for multi-stock comparison.

GET /api/v1/compare?tickers=RELIANCE.NS,TCS.NS,INFY.NS

?tickers: comma-separated or repeated query params (FastAPI handles both)
Validates: 2–10 tickers required, all must be tracked
"""

import logging

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_comparison_service
from app.schemas.stock_schema import CompareResponse
from app.services.comparison_service import ComparisonService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=CompareResponse,
    summary="Compare multiple stocks",
    description=(
        "Returns current market data for 2–10 ticker symbols side by side. "
        "Pass tickers as repeated params: ?tickers=RELIANCE.NS&tickers=TCS.NS "
        "or comma-separated: ?tickers=RELIANCE.NS,TCS.NS. "
        "All tickers must be registered in the tracking database."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "One or more tickers not found"},
        422: {"description": "Fewer than 2 or more than 10 tickers provided"},
    },
)
async def compare_stocks(
    tickers: list[str] = Query(
        ...,
        description="Ticker symbols to compare (2–10). Can be repeated or comma-separated.",
        examples=[["RELIANCE.NS", "TCS.NS", "INFY.NS"]],
    ),
    service: ComparisonService = Depends(get_comparison_service),
) -> CompareResponse:
    # Support comma-separated in a single param: ?tickers=RELIANCE.NS,TCS.NS
    expanded: list[str] = []
    for t in tickers:
        expanded.extend(t.split(","))
    cleaned = [t.strip() for t in expanded if t.strip()]

    return await service.compare_stocks(cleaned)
