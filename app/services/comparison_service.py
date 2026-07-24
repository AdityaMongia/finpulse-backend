"""
app/services/comparison_service.py
====================================
Business logic for multi-stock comparison.

GET /compare?tickers=RELIANCE,TCS,INFY
"""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError, NotFoundError, ValidationError
from app.repositories.company_repository import CompanyRepository
from app.schemas.stock_schema import CompareItemResponse, CompareResponse

logger = logging.getLogger(__name__)

_MIN_TICKERS = 2
_MAX_TICKERS = 10


class ComparisonService:
    """Handles multi-stock comparison business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.company_repo = CompanyRepository(db)

    async def compare_stocks(self, tickers: list[str]) -> CompareResponse:
        """
        Fetch and compare current market data for multiple tickers.

        Business rules enforced here:
          - At least 2 tickers required
          - No more than 10 tickers allowed
          - All tickers must exist in the database

        Parameters
        ----------
        tickers : list[str]
            Ticker symbols to compare.

        Returns
        -------
        CompareResponse
            Companies list matching spec Section 6.2 format.

        Raises
        ------
        ValidationError : fewer than 2 or more than 10 tickers
        NotFoundError   : any ticker not found in the database
        DatabaseError   : unexpected DB failure
        """
        # --- Validate count ---
        if len(tickers) < _MIN_TICKERS:
            raise ValidationError(
                f"At least {_MIN_TICKERS} tickers are required for comparison. "
                f"Provided: {len(tickers)}."
            )
        if len(tickers) > _MAX_TICKERS:
            raise ValidationError(
                f"Maximum {_MAX_TICKERS} tickers allowed for comparison. "
                f"Provided: {len(tickers)}."
            )

        # --- Deduplicate while preserving order ---
        seen: set[str] = set()
        unique_tickers: list[str] = []
        for t in tickers:
            upper = t.upper()
            if upper not in seen:
                seen.add(upper)
                unique_tickers.append(upper)

        # --- Fetch all from DB (single query with JOIN) ---
        try:
            companies = await self.company_repo.get_by_tickers_with_market_data(
                unique_tickers
            )
        except SQLAlchemyError as exc:
            logger.exception("DB error fetching comparison data for %s", unique_tickers)
            raise DatabaseError() from exc

        # --- Detect missing tickers ---
        found_tickers = {c.ticker.upper() for c in companies}
        missing = [t for t in unique_tickers if t not in found_tickers]
        if missing:
            raise NotFoundError(
                detail=f"The following ticker(s) are not tracked: {', '.join(missing)}. "
                       f"Register them first via POST /api/v1/stocks/."
            )

        # --- Build response --- 
        items = []
        for company in companies:
            md = company.market_data
            items.append(
                CompareItemResponse(
                    ticker=company.ticker,
                    company_name=company.company_name,
                    exchange=company.exchange,
                    sector=company.sector,
                    current_price=md.current_price if md else None,
                    market_cap=md.market_cap if md else None,
                    pe_ratio=md.pe_ratio if md else None,
                    eps=md.eps if md else None,
                    volume=md.volume if md else None,
                    fifty_two_week_high=md.fifty_two_week_high if md else None,
                    fifty_two_week_low=md.fifty_two_week_low if md else None,
                    last_updated=md.last_updated if md else None,
                )
            )

        return CompareResponse(companies=items)
