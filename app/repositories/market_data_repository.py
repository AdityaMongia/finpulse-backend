"""
app/repositories/market_data_repository.py
============================================
Data access layer for the `market_data` table.

The most important method here is `upsert()` — it uses PostgreSQL's
INSERT ... ON CONFLICT DO UPDATE to atomically create-or-update a row.
This is what makes live price refreshes idempotent.

INSERT ... ON CONFLICT (company_id) DO UPDATE SET
    current_price = EXCLUDED.current_price,
    volume        = EXCLUDED.volume,
    last_updated  = NOW()
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import MarketData
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MarketDataRepository(BaseRepository[MarketData]):
    """Repository for the `market_data` table."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=MarketData, db=db)

    # ------------------------------------------------------------------
    # Single-company lookup
    # ------------------------------------------------------------------

    async def get_by_company_id(self, company_id: int) -> MarketData | None:
        """Fetch the market data snapshot for a single company."""
        result = await self.db.execute(
            select(MarketData).where(MarketData.company_id == company_id)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Upsert (CREATE or UPDATE atomically)
    # ------------------------------------------------------------------

    async def upsert(self, company_id: int, **data: Any) -> MarketData:
        """
        Insert or update market data for a company (atomic upsert).

        Uses PostgreSQL's `INSERT ... ON CONFLICT (company_id) DO UPDATE`
        so this is safe to call multiple times — always results in one row
        per company with the latest values.

        Parameters
        ----------
        company_id : int
            The company whose data to upsert.
        **data : Any
            Field values: current_price, pe_ratio, eps, market_cap, volume,
            fifty_two_week_high, fifty_two_week_low, dividend_yield.

        Example:
            await repo.upsert(
                company_id=1,
                current_price=2945.30,
                volume=5123400,
            )
        """
        insert_values = {
            "company_id": company_id,
            "last_updated": datetime.now(timezone.utc),
            **{k: v for k, v in data.items() if v is not None},
        }

        # Only update non-None values to avoid overwriting valid data with NULL
        update_values = {
            k: v for k, v in insert_values.items()
            if k != "company_id"
        }
        update_values["last_updated"] = datetime.now(timezone.utc)

        stmt = (
            pg_insert(MarketData)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=["company_id"],
                set_=update_values,
            )
            .returning(MarketData)
        )

        result = await self.db.execute(stmt)
        await self.db.flush()
        row = result.fetchone()

        logger.debug("Upserted market_data for company_id=%d", company_id)
        return row[0] if row else await self.get_by_company_id(company_id)  # type: ignore

    # ------------------------------------------------------------------
    # Aggregate stats for /market-summary
    # ------------------------------------------------------------------

    async def get_aggregate_stats(self, sector: str | None = None) -> dict[str, Any]:
        """
        Compute aggregate statistics across all companies (or filtered by sector).

        Returns:
          - total_companies : int
          - avg_pe_ratio    : float | None
          - highest_market_cap : int | None
          - highest_market_cap_ticker : str | None
          - last_updated    : datetime | None (most recent refresh)

        Used by: GET /market-summary
        """
        from app.models.company import Company

        agg_query = (
            select(
                func.count(MarketData.id).label("total_companies"),
                func.avg(MarketData.pe_ratio).label("avg_pe_ratio"),
                func.max(MarketData.market_cap).label("highest_market_cap"),
                func.sum(MarketData.market_cap).label("total_market_cap"),
                func.max(MarketData.last_updated).label("last_updated"),
            )
            .join(Company, MarketData.company_id == Company.id)
        )

        top_company_query = (
            select(Company.ticker, Company.company_name)
            .join(MarketData, MarketData.company_id == Company.id)
            .order_by(MarketData.market_cap.desc().nullslast())
            .limit(1)
        )

        if sector and sector.strip():
            agg_query = agg_query.where(Company.sector.ilike(f"%{sector.strip()}%"))
            top_company_query = top_company_query.where(Company.sector.ilike(f"%{sector.strip()}%"))

        agg_result = await self.db.execute(agg_query)
        agg_row = agg_result.fetchone()

        top_company_result = await self.db.execute(top_company_query)
        top_company = top_company_result.fetchone()

        return {
            "total_companies": agg_row.total_companies if agg_row else 0,
            "avg_pe_ratio": (
                round(float(agg_row.avg_pe_ratio), 2)
                if agg_row and agg_row.avg_pe_ratio is not None
                else None
            ),
            "highest_market_cap": (
                int(agg_row.highest_market_cap)
                if agg_row and agg_row.highest_market_cap is not None
                else None
            ),
            "total_market_cap": (
                int(agg_row.total_market_cap)
                if agg_row and agg_row.total_market_cap is not None
                else None
            ),
            "highest_market_cap_ticker": top_company.ticker if top_company else None,
            "highest_market_cap_company": top_company.company_name if top_company else None,
            "last_updated": agg_row.last_updated if agg_row else None,
        }
