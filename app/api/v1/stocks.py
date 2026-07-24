"""
app/api/v1/stocks.py
=====================
Route handlers for stock and company endpoints.

GET  /api/v1/stocks/         → Paginated list with optional ?sector= filter
GET  /api/v1/stocks/{ticker} → Full detail for one company (404 if not tracked)
POST /api/v1/stocks/         → Register a new stock to track
"""

import logging

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_stock_service
from app.schemas.stock_schema import (
    CompanyCreateRequest,
    CompanyResponse,
    StockDetailResponse,
    StockListResponse,
)
from app.services.stock_service import StockService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=StockListResponse,
    summary="List all tracked stocks",
    description=(
        "Returns a paginated list of all companies currently tracked by FinPulse, "
        "with their latest market data. Filter by sector using ?sector=Energy."
    ),
    status_code=status.HTTP_200_OK,
)
async def list_stocks(
    sector: str | None = Query(
        None,
        description="Filter by sector (case-insensitive). E.g. ?sector=Energy",
        examples=["Energy"],
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: StockService = Depends(get_stock_service),
) -> StockListResponse:
    return await service.list_stocks(sector=sector, page=page, page_size=page_size)


@router.get(
    "/{ticker}",
    response_model=StockDetailResponse,
    summary="Get stock detail",
    description=(
        "Returns full company info and current market data for the given ticker. "
        "Returns 404 if the ticker is not currently tracked by FinPulse."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Ticker not found in the tracking database"},
    },
)
async def get_stock_detail(
    ticker: str,
    service: StockService = Depends(get_stock_service),
) -> StockDetailResponse:
    return await service.get_stock_detail(ticker)


@router.post(
    "/",
    response_model=CompanyResponse,
    summary="Register a stock for tracking",
    description=(
        "Add a new company/ticker to the FinPulse tracking database. "
        "The scheduler will automatically fetch its market data on the next cycle."
    ),
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Ticker already registered"},
    },
)
async def register_stock(
    request: CompanyCreateRequest,
    service: StockService = Depends(get_stock_service),
) -> CompanyResponse:
    return await service.register_company(request)
