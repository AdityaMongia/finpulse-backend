"""
app/services/stock_service.py
==============================
Business logic for stock, company, and market summary operations.

This service:
  - Orchestrates repositories (no SQL here)
  - Enforces business rules
  - Raises domain exceptions (NotFoundError, etc.)
  - Has zero knowledge of HTTP (no Request/Response objects)

Dependency injection:
  Repositories are created from the injected AsyncSession.
  The YFinanceClient is instantiated internally (stateless).
"""

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, DatabaseError, NotFoundError
from app.repositories.company_repository import CompanyRepository
from app.repositories.historical_price_repository import (
    HistoricalPriceRepository,
    RANGE_DAYS,
)
from app.repositories.market_data_repository import MarketDataRepository
from app.schemas.stock_schema import (
    CompanyCreateRequest,
    CompanyResponse,
    MarketDataResponse,
    StockDetailResponse,
    StockListItemResponse,
    StockListResponse,
)
from app.schemas.market_summary_schema import MarketSummaryResponse
from app.schemas.historical_schema import HistoricalPriceRecord, HistoricalPriceResponse
from app.services.yfinance_client import YFinanceClient

logger = logging.getLogger(__name__)


class StockService:
    """Handles all business logic for companies, market data, and historical prices."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.company_repo = CompanyRepository(db)
        self.market_data_repo = MarketDataRepository(db)
        self.historical_repo = HistoricalPriceRepository(db)
        self.yf_client = YFinanceClient()

    # ------------------------------------------------------------------
    # GET /stocks — paginated list
    # ------------------------------------------------------------------

    async def list_stocks(
        self,
        sector: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> StockListResponse:
        """
        Return a paginated list of tracked companies with their latest market data.

        Parameters
        ----------
        sector : str | None
            Optional filter by sector name (case-insensitive).
        page : int
            1-indexed page number.
        page_size : int
            Results per page (max 100).
        """
        try:
            offset = (page - 1) * page_size
            companies = await self.company_repo.get_all_with_market_data(
                sector=sector, offset=offset, limit=page_size
            )
            total = await self.company_repo.count_by_sector(sector=sector)
        except SQLAlchemyError as exc:
            logger.exception("DB error listing stocks")
            raise DatabaseError() from exc

        items = []
        for company in companies:
            md = company.market_data
            items.append(
                StockListItemResponse(
                    ticker=company.ticker,
                    company_name=company.company_name,
                    exchange=company.exchange,
                    sector=company.sector,
                    current_price=md.current_price if md else None,
                    market_cap=md.market_cap if md else None,
                    pe_ratio=md.pe_ratio if md else None,
                    volume=md.volume if md else None,
                    last_updated=md.last_updated if md else None,
                )
            )

        return StockListResponse(
            total=total,
            page=page,
            page_size=page_size,
            sector_filter=sector,
            stocks=items,
        )

    # ------------------------------------------------------------------
    # GET /stocks/{ticker} — full detail
    # ------------------------------------------------------------------

    async def get_stock_detail(self, ticker: str) -> StockDetailResponse:
        """
        Return full company info + market data for one ticker.

        Raises:
            NotFoundError: if ticker is not tracked in the database.
            DatabaseError: on unexpected DB failure.
        """
        try:
            company = await self.company_repo.get_by_ticker_with_market_data(ticker)
        except SQLAlchemyError as exc:
            logger.exception("DB error fetching stock detail for %s", ticker)
            raise DatabaseError() from exc

        if company is None:
            raise NotFoundError(resource="Stock", identifier=ticker)

        md = company.market_data
        market_data_response = None
        if md:
            market_data_response = MarketDataResponse(
                current_price=md.current_price,
                market_cap=md.market_cap,
                pe_ratio=md.pe_ratio,
                eps=md.eps,
                volume=md.volume,
                fifty_two_week_high=md.fifty_two_week_high,
                fifty_two_week_low=md.fifty_two_week_low,
                dividend_yield=md.dividend_yield,
                last_updated=md.last_updated,
            )

        return StockDetailResponse(
            ticker=company.ticker,
            company_name=company.company_name,
            exchange=company.exchange,
            sector=company.sector,
            industry=company.industry,
            market_data=market_data_response,
        )

    # ------------------------------------------------------------------
    # POST /stocks — register new ticker
    # ------------------------------------------------------------------

    async def register_company(self, request: CompanyCreateRequest) -> CompanyResponse:
        """
        Register a new company for tracking.

        Steps:
          1. Check if ticker already exists (ConflictError if so)
          2. Create the company row
          3. Create an empty market_data row (will be filled by scheduler)

        Raises:
            ConflictError: if the ticker is already tracked.
            DatabaseError: on unexpected DB failure.
        """
        try:
            existing = await self.company_repo.get_by_ticker(request.ticker)
            if existing:
                raise ConflictError(resource="Stock", identifier=request.ticker)

            company = await self.company_repo.create(
                ticker=request.ticker.upper(),
                company_name=request.company_name,
                exchange=request.exchange.upper(),
                sector=request.sector,
                industry=request.industry,
            )

            # Create empty market_data row so JOINs don't return NULL
            await self.market_data_repo.upsert(company_id=company.id)

        except (ConflictError, DatabaseError):
            raise
        except SQLAlchemyError as exc:
            logger.exception("DB error registering company %s", request.ticker)
            raise DatabaseError() from exc

        logger.info("Registered new company: %s", company.ticker)
        return CompanyResponse(
            id=company.id,
            ticker=company.ticker,
            company_name=company.company_name,
            exchange=company.exchange,
            sector=company.sector,
            industry=company.industry,
        )

    # ------------------------------------------------------------------
    # GET /search?q=
    # ------------------------------------------------------------------

    async def search_stocks(
        self, query: str, exchange: str | None = None
    ) -> list[CompanyResponse]:
        """
        Search companies by ticker or name using case-insensitive ILIKE.

        Returns:
            list of matching companies (max 20)
        """
        try:
            companies = await self.company_repo.search(
                query=query, exchange=exchange, limit=20
            )
        except SQLAlchemyError as exc:
            logger.exception("DB error searching stocks for q=%s", query)
            raise DatabaseError() from exc

        return [
            CompanyResponse(
                id=c.id,
                ticker=c.ticker,
                company_name=c.company_name,
                exchange=c.exchange,
                sector=c.sector,
                industry=c.industry,
            )
            for c in companies
        ]

    # ------------------------------------------------------------------
    # GET /historical/{ticker}?range=
    # ------------------------------------------------------------------

    async def get_historical_prices(
        self, ticker: str, range_param: str = "1m"
    ) -> HistoricalPriceResponse:
        """
        Fetch stored OHLCV data for a ticker over a named range.

        Validates:
          - Ticker must exist (NotFoundError otherwise)
          - range_param must be one of 1m, 3m, 6m, 1y

        Returns empty prices list (HTTP 200) if no data exists yet.
        """
        if range_param not in RANGE_DAYS:
            from app.core.exceptions import ValidationError
            raise ValidationError(
                f"Invalid range '{range_param}'. Valid options: {', '.join(RANGE_DAYS)}"
            )

        try:
            company = await self.company_repo.get_by_ticker(ticker)
        except SQLAlchemyError as exc:
            raise DatabaseError() from exc

        if company is None:
            raise NotFoundError(resource="Stock", identifier=ticker)

        try:
            rows = await self.historical_repo.get_by_company_and_range(
                company_id=company.id, range_param=range_param
            )
        except SQLAlchemyError as exc:
            raise DatabaseError() from exc

        price_records = [
            HistoricalPriceRecord(
                date=row.date,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            )
            for row in rows
        ]

        return HistoricalPriceResponse(
            ticker=company.ticker,
            company_name=company.company_name,
            date_range=range_param,
            total_records=len(price_records),
            prices=price_records,
        )

    # ------------------------------------------------------------------
    # GET /market-summary
    # ------------------------------------------------------------------

    async def get_market_summary(self, sector: str | None = None) -> MarketSummaryResponse:
        """
        Compute and return aggregate market stats across all tracked companies (or a specific sector).

        All values are computed on read (not stored) — per spec requirement.

        Raises:
            DatabaseError: on unexpected DB failure.
        """
        try:
            stats = await self.market_data_repo.get_aggregate_stats(sector=sector)
        except SQLAlchemyError as exc:
            logger.exception("DB error computing market summary")
            raise DatabaseError() from exc

        return MarketSummaryResponse(**stats)

    # ------------------------------------------------------------------
    # Scheduler-facing refresh methods
    # ------------------------------------------------------------------

    async def refresh_live_price(self, ticker: str, company_id: int) -> None:
        """
        Fetch and persist current price + volume for one ticker.
        Called by `refresh_live_prices` scheduler job.
        """
        try:
            data = await self.yf_client.get_live_price_and_volume(ticker)
            await self.market_data_repo.upsert(company_id=company_id, **data)
        except Exception as exc:
            # Log and skip — don't let one bad ticker crash the entire batch
            logger.warning(
                "Failed to refresh live price for %s: %s", ticker, exc
            )

    async def refresh_fundamentals(self, ticker: str, company_id: int) -> None:
        """
        Fetch and persist PE, EPS, market cap, 52w range for one ticker.
        Called by `refresh_fundamentals` scheduler job.
        """
        try:
            data = await self.yf_client.get_fundamentals(ticker)
            await self.market_data_repo.upsert(company_id=company_id, **data)
        except Exception as exc:
            logger.warning(
                "Failed to refresh fundamentals for %s: %s", ticker, exc
            )

    async def refresh_historical(self, ticker: str, company_id: int) -> None:
        """
        Fetch today's OHLCV and append to historical_prices.
        Called by `refresh_historical` scheduler job.
        Uses bulk_upsert (ON CONFLICT DO NOTHING) for idempotency.
        """
        try:
            rows = await self.yf_client.get_historical_prices(ticker, period="2d")
            if not rows:
                logger.info("No historical data returned for %s — skipping", ticker)
                return

            records = [{"company_id": company_id, **row} for row in rows]
            inserted = await self.historical_repo.bulk_upsert(records)
            logger.debug("Historical refresh for %s: %d row(s) inserted", ticker, inserted)
        except Exception as exc:
            logger.warning(
                "Failed to refresh historical for %s: %s", ticker, exc
            )
