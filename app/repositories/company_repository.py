"""
app/repositories/company_repository.py
========================================
Data access layer for the `companies` table.

All SQL in this file. No business logic. No HTTP concerns.
Inherits generic CRUD from BaseRepository[Company].

Custom queries added here:
  - get_by_ticker      → used by every endpoint that receives a ticker param
  - search             → used by /search endpoint (ILIKE name/ticker)
  - get_all_with_market_data → used by /stocks list (avoids N+1 via JOIN)
"""

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.base import Base
from app.models.company import Company
from app.models.market_data import MarketData
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class CompanyRepository(BaseRepository[Company]):
    """Repository for the `companies` table."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Company, db=db)

    # ------------------------------------------------------------------
    # Lookup by ticker
    # ------------------------------------------------------------------

    async def get_by_ticker(self, ticker: str) -> Company | None:
        """
        Fetch a company by its ticker symbol (case-insensitive).

        Returns None if the ticker is not tracked — let the service
        layer decide whether to raise NotFoundError.

        Example:
            company = await repo.get_by_ticker("reliance.ns")
            # matches "RELIANCE.NS" in the database
        """
        result = await self.db.execute(
            select(Company).where(
                func.upper(Company.ticker) == ticker.upper()
            )
        )
        return result.scalar_one_or_none()

    async def get_by_ticker_with_market_data(self, ticker: str) -> Company | None:
        """
        Fetch a company and eagerly load its market_data in a single query.

        Uses selectinload to avoid the N+1 problem: instead of one query for
        the company then another for market_data, SQLAlchemy issues one
        optimised JOIN.
        """
        result = await self.db.execute(
            select(Company)
            .options(selectinload(Company.market_data))
            .where(func.upper(Company.ticker) == ticker.upper())
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # List with optional filters
    # ------------------------------------------------------------------

    async def get_all_with_market_data(
        self,
        *,
        sector: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Company]:
        """
        Fetch paginated companies with their market_data pre-loaded.

        Parameters
        ----------
        sector : str | None
            If provided, filter by sector (case-insensitive exact match).
        offset : int
            Pagination offset.
        limit : int
            Maximum records to return (max 100).

        Used by: GET /stocks
        """
        query = (
            select(Company)
            .options(selectinload(Company.market_data))
            .order_by(Company.ticker)
            .offset(offset)
            .limit(min(limit, 100))
        )

        if sector:
            query = query.where(
                func.upper(Company.sector) == sector.upper()
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_sector(self, sector: str | None = None) -> int:
        """Count companies, optionally filtered by sector (for pagination meta)."""
        query = select(func.count()).select_from(Company)
        if sector:
            query = query.where(func.upper(Company.sector) == sector.upper())
        result = await self.db.execute(query)
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        exchange: str | None = None,
        limit: int = 20,
    ) -> list[Company]:
        """
        Fuzzy search on ticker symbol and company name using ILIKE.

        ILIKE is PostgreSQL's case-insensitive LIKE.
        The `%query%` pattern matches any substring.

        Parameters
        ----------
        query : str
            Search term (partial ticker or company name).
        exchange : str | None
            Optional exchange filter (NSE or BSE).
        limit : int
            Max results to return.

        Used by: GET /search?q=
        """
        search_term = f"%{query}%"

        stmt = (
            select(Company)
            .where(
                or_(
                    Company.ticker.ilike(search_term),
                    Company.company_name.ilike(search_term),
                )
            )
            .order_by(Company.ticker)
            .limit(limit)
        )

        if exchange:
            stmt = stmt.where(
                func.upper(Company.exchange) == exchange.upper()
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Comparison (multi-ticker fetch)
    # ------------------------------------------------------------------

    async def get_by_tickers_with_market_data(
        self, tickers: list[str]
    ) -> list[Company]:
        """
        Fetch multiple companies by ticker list, with market_data pre-loaded.

        Used by: GET /compare?tickers=RELIANCE,TCS,INFY
        """
        upper_tickers = [t.upper() for t in tickers]
        result = await self.db.execute(
            select(Company)
            .options(selectinload(Company.market_data))
            .where(func.upper(Company.ticker).in_(upper_tickers))
            .order_by(Company.ticker)
        )
        return list(result.scalars().all())
