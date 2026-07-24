"""
app/api/v1/search.py
=====================
Route handler for stock search.

GET /api/v1/search?q=reliance
GET /api/v1/search?q=TCS&exchange=NSE

Returns max 20 results. Fuzzy match on ticker and company name via ILIKE.
"""

import logging

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_stock_service
from app.schemas.stock_schema import CompanyResponse
from app.services.stock_service import StockService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=list[CompanyResponse],
    summary="Search stocks",
    description=(
        "Search for companies by ticker symbol or company name. "
        "Case-insensitive partial match. Returns up to 20 results. "
        "Optionally filter by exchange using ?exchange=NSE or ?exchange=BSE."
    ),
    status_code=status.HTTP_200_OK,
)
async def search_stocks(
    q: str = Query(
        ...,
        min_length=1,
        description="Search term — partial ticker or company name",
        examples=["Reliance"],
    ),
    exchange: str | None = Query(
        None,
        description="Optional exchange filter: NSE or BSE",
        examples=["NSE"],
    ),
    service: StockService = Depends(get_stock_service),
) -> list[CompanyResponse]:
    return await service.search_stocks(query=q, exchange=exchange)
