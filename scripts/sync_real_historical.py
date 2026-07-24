"""
scripts/sync_real_historical.py
=================================
Script to fetch real 1-year historical OHLCV data from Yahoo Finance
and replace the synthetic mock historical prices in the database.
"""

import asyncio
import os
import sys
import logging
from decimal import Decimal
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.config import settings
from app.repositories.company_repository import CompanyRepository
from app.repositories.historical_price_repository import HistoricalPriceRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sync_real_historical")

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def sync_company_history(session: AsyncSession, company_id: int, ticker: str):
    logger.info("Fetching real 1y historical data for %s from Yahoo Finance...", ticker)
    
    # Run yfinance download in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(
        None,
        lambda: yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
    )

    if df is None or df.empty:
        logger.warning("No historical data returned for %s", ticker)
        return 0

    # Delete existing mock/synthetic historical rows for this company
    await session.execute(
        text("DELETE FROM historical_prices WHERE company_id = :cid"),
        {"cid": company_id}
    )

    rows_to_insert = []
    for idx, row in df.iterrows():
        try:
            # Handle MultiIndex columns if present in yfinance DataFrame
            open_val = row["Open"].iloc[0] if hasattr(row["Open"], "iloc") else row["Open"]
            high_val = row["High"].iloc[0] if hasattr(row["High"], "iloc") else row["High"]
            low_val = row["Low"].iloc[0] if hasattr(row["Low"], "iloc") else row["Low"]
            close_val = row["Close"].iloc[0] if hasattr(row["Close"], "iloc") else row["Close"]
            vol_val = row["Volume"].iloc[0] if hasattr(row["Volume"], "iloc") else row["Volume"]

            if any(p is None or str(p) == "nan" for p in [open_val, high_val, low_val, close_val]):
                continue

            dt = idx.date() if hasattr(idx, "date") else idx

            rows_to_insert.append({
                "company_id": company_id,
                "date": dt,
                "open": Decimal(str(round(float(open_val), 2))),
                "high": Decimal(str(round(float(high_val), 2))),
                "low": Decimal(str(round(float(low_val), 2))),
                "close": Decimal(str(round(float(close_val), 2))),
                "volume": int(vol_val),
            })
        except Exception as e:
            logger.warning("Skipping row for %s date %s: %s", ticker, idx, e)

    if rows_to_insert:
        historical_repo = HistoricalPriceRepository(session)
        await historical_repo.bulk_upsert(rows_to_insert)
        logger.info("Inserted %d real OHLCV rows for %s", len(rows_to_insert), ticker)

    return len(rows_to_insert)


async def main():
    async with AsyncSessionLocal() as session:
        company_repo = CompanyRepository(session)
        companies = await company_repo.get_all_with_market_data(offset=0, limit=500)
        logger.info("Found %d tracked companies in database.", len(companies))

        total_inserted = 0
        for company in companies:
            try:
                inserted = await sync_company_history(session, company.id, company.ticker)
                total_inserted += inserted
                await session.commit()
            except Exception as e:
                logger.error("Failed to sync historical data for %s: %s", company.ticker, e)

        logger.info("DONE! Total %d real historical rows synced across all companies.", total_inserted)


if __name__ == "__main__":
    asyncio.run(main())
