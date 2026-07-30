"""
scripts/seed_db.py
==================
One-time database seeder for FinPulse.

Seeds 20 popular NSE stocks:
  1. Registers each company (if not already present)
  2. Fetches live market data from yFinance and upserts to market_data table
  3. Fetches 1-year historical OHLCV and inserts into historical_prices table

Usage:
    cd u:\\Finpulse\\finpulse-backend
    python scripts/seed_db.py

Requirements:
  - Backend database must be running (Local PostgreSQL on port 5432)
  - Alembic migrations must have been applied (python -m alembic upgrade head)
  - All pip packages must be installed (pip install -r requirements.txt)
"""

import asyncio
import logging
import sys
import os

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.repositories.company_repository import CompanyRepository
from app.repositories.market_data_repository import MarketDataRepository
from app.repositories.historical_price_repository import HistoricalPriceRepository
from app.services.yfinance_client import YFinanceClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed")

# ── 20 NSE Tickers to seed ────────────────────────────────────────────────────
TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "HINDUNILVR.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "KOTAKBANK.NS",
    "WIPRO.NS",
    "AXISBANK.NS",
    "LTIM.NS",
    "HCLTECH.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "NESTLEIND.NS",
    "ASIANPAINT.NS",
    "POWERGRID.NS",
    "NTPC.NS",
]

# ── DB session setup ──────────────────────────────────────────────────────────

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

yf_client = YFinanceClient()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def seed_ticker(session: AsyncSession, ticker: str) -> bool:
    """Returns True if fully seeded, False if skipped due to error."""
    company_repo   = CompanyRepository(session)
    market_repo    = MarketDataRepository(session)
    historical_repo = HistoricalPriceRepository(session)

    # ── Step 1: Register company ──────────────────────────────────────────────
    existing = await company_repo.get_by_ticker(ticker)
    if existing:
        logger.info("%-20s  already registered (id=%d)", ticker, existing.id)
        company = existing
    else:
        logger.info("%-20s  fetching company info from yFinance...", ticker)
        try:
            info = await yf_client.get_company_info(ticker)
        except Exception as e:
            logger.error("%-20s  SKIP — company info failed: %s", ticker, e)
            return False

        company = await company_repo.create(
            ticker=ticker,
            company_name=info.get("company_name", ticker),
            exchange=info.get("exchange", "NSE"),
            sector=info.get("sector"),
            industry=info.get("industry"),
        )
        logger.info(
            "%-20s  registered → %s | %s",
            ticker, company.company_name, company.sector or "—"
        )

    # ── Step 2: Market data (current quote) ───────────────────────────────────
    logger.info("%-20s  fetching market data...", ticker)
    try:
        quote = await yf_client.get_current_quote(ticker)
        await market_repo.upsert(company_id=company.id, **quote)
        logger.info(
            "%-20s  market data ✓  price=₹%s  mcap=%s",
            ticker,
            quote.get("current_price", "—"),
            f"{quote.get('market_cap', 0):,}" if quote.get("market_cap") else "—",
        )
    except Exception as e:
        logger.warning("%-20s  market data SKIP — %s", ticker, e)
        # Still create empty row so JOINs don't break
        await market_repo.upsert(company_id=company.id)

    # ── Step 3: Historical OHLCV (1 year) ─────────────────────────────────────
    logger.info("%-20s  fetching 1y historical data...", ticker)
    try:
        rows = await yf_client.get_historical_prices(ticker, period="1y")
        if rows:
            records = [{"company_id": company.id, **row} for row in rows]
            inserted = await historical_repo.bulk_upsert(records)
            logger.info("%-20s  historical  ✓  %d days inserted", ticker, inserted)
        else:
            logger.warning("%-20s  historical  empty (new/delisted?)", ticker)
    except Exception as e:
        logger.warning("%-20s  historical  SKIP — %s", ticker, e)

    return True


async def main() -> None:
    logger.info("=" * 60)
    logger.info("FinPulse DB Seeder — %d tickers", len(TICKERS))
    logger.info("DB: %s", settings.DATABASE_URL.split("@")[-1])
    logger.info("=" * 60)

    success, failed, skipped = 0, 0, 0

    async with AsyncSessionLocal() as session:
        for i, ticker in enumerate(TICKERS, 1):
            logger.info("\n[%d/%d] %s", i, len(TICKERS), ticker)
            try:
                result = await seed_ticker(session, ticker)
                await session.commit()
                if result:
                    success += 1
                else:
                    skipped += 1
            except Exception as e:
                await session.rollback()
                logger.error("%-20s  FAILED — %s", ticker, e)
                failed += 1

            # Rate-limit protection: 3s delay between tickers
            if i < len(TICKERS):
                await asyncio.sleep(3)

    logger.info("\n" + "=" * 60)
    logger.info("Seeding complete: %d seeded, %d skipped (rate-limited), %d failed", success, skipped, failed)
    logger.info("=" * 60)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
