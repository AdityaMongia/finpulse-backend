"""
app/repositories/historical_price_repository.py
=================================================
Data access layer for the `historical_prices` table.

Key method: `bulk_upsert()` uses INSERT ... ON CONFLICT DO NOTHING to
insert multiple rows atomically. The UNIQUE(company_id, date) constraint
ensures this is idempotent — running the daily job twice produces exactly
the same data as running it once.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.historical_price import HistoricalPrice
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

# Mapping of ?range= query param → number of calendar days
RANGE_DAYS: dict[str, int] = {
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
}


class HistoricalPriceRepository(BaseRepository[HistoricalPrice]):
    """Repository for the `historical_prices` table."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=HistoricalPrice, db=db)

    # ------------------------------------------------------------------
    # Range-based lookups
    # ------------------------------------------------------------------

    async def get_by_company_and_range(
        self,
        company_id: int,
        range_param: str = "1m",
    ) -> list[HistoricalPrice]:
        """
        Fetch OHLCV rows for a company over a named date range.

        Parameters
        ----------
        company_id : int
            PK of the company.
        range_param : str
            One of: "1m", "3m", "6m", "1y"
            Defaults to "1m" if an unrecognised value is supplied.

        Returns rows in ascending date order.

        Used by: GET /historical/{ticker}?range=3m
        """
        days = RANGE_DAYS.get(range_param, RANGE_DAYS["1m"])
        start_date = date.today() - timedelta(days=days)

        result = await self.db.execute(
            select(HistoricalPrice)
            .where(
                HistoricalPrice.company_id == company_id,
                HistoricalPrice.date >= start_date,
            )
            .order_by(HistoricalPrice.date.asc())
        )
        return list(result.scalars().all())

    async def get_by_company_and_dates(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
    ) -> list[HistoricalPrice]:
        """
        Fetch OHLCV rows for a company within an explicit date range.

        Parameters
        ----------
        company_id : int
        start_date : date  (inclusive)
        end_date   : date  (inclusive)
        """
        result = await self.db.execute(
            select(HistoricalPrice)
            .where(
                HistoricalPrice.company_id == company_id,
                HistoricalPrice.date >= start_date,
                HistoricalPrice.date <= end_date,
            )
            .order_by(HistoricalPrice.date.asc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Bulk idempotent insert
    # ------------------------------------------------------------------

    async def bulk_upsert(
        self, records: list[dict[str, Any]]
    ) -> int:
        """
        Insert multiple OHLCV rows, skipping duplicates.

        Uses: INSERT ... ON CONFLICT (company_id, date) DO NOTHING

        This makes the daily scheduler job idempotent:
          - Run it once → all rows inserted
          - Run it again (redeployment, job retry) → 0 new rows, no error

        Parameters
        ----------
        records : list[dict]
            Each dict must have keys:
              company_id, date, open, high, low, close, volume

        Returns
        -------
        int
            Number of rows actually inserted (0 if all were duplicates).
        """
        if not records:
            return 0

        stmt = (
            pg_insert(HistoricalPrice)
            .values(records)
            .on_conflict_do_nothing(
                index_elements=["company_id", "date"]
            )
        )

        result = await self.db.execute(stmt)
        await self.db.flush()

        inserted = result.rowcount
        logger.debug(
            "bulk_upsert: attempted=%d inserted=%d",
            len(records),
            inserted,
        )
        return inserted
