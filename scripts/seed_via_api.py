"""
scripts/seed_via_api.py
========================
Seed 20 NSE companies by calling the running FastAPI backend directly.
No SQLAlchemy session issues - uses the actual HTTP API.

Usage:
    cd u:\\Finpulse\\finpulse-backend
    python scripts/seed_via_api.py

Requirements:
    Backend must be running: python -m uvicorn app.main:app --port 8005
"""

import time
import asyncio
import asyncpg
import yfinance as yf
import httpx
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_api")

API_BASE  = "http://localhost:8005/api/v1"
import os
DB_DSN    = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/finpulse_db").replace("postgresql+asyncpg://", "postgresql://")

# 20 NSE companies with static info (avoids .info rate limits for registration)
COMPANIES = [
    {"ticker": "RELIANCE.NS",   "company_name": "Reliance Industries Limited",          "exchange": "NSE", "sector": "Energy",                      "industry": "Oil & Gas Refining & Marketing"},
    {"ticker": "TCS.NS",        "company_name": "Tata Consultancy Services Limited",    "exchange": "NSE", "sector": "Information Technology",       "industry": "IT Services & Consulting"},
    {"ticker": "INFY.NS",       "company_name": "Infosys Limited",                      "exchange": "NSE", "sector": "Information Technology",       "industry": "IT Services & Consulting"},
    {"ticker": "HDFCBANK.NS",   "company_name": "HDFC Bank Limited",                    "exchange": "NSE", "sector": "Financial Services",           "industry": "Banks - Private Sector"},
    {"ticker": "ICICIBANK.NS",  "company_name": "ICICI Bank Limited",                   "exchange": "NSE", "sector": "Financial Services",           "industry": "Banks - Private Sector"},
    {"ticker": "HINDUNILVR.NS", "company_name": "Hindustan Unilever Limited",           "exchange": "NSE", "sector": "Consumer Goods",               "industry": "FMCG"},
    {"ticker": "SBIN.NS",       "company_name": "State Bank of India",                  "exchange": "NSE", "sector": "Financial Services",           "industry": "Banks - Public Sector"},
    {"ticker": "BHARTIARTL.NS", "company_name": "Bharti Airtel Limited",                "exchange": "NSE", "sector": "Communication Services",       "industry": "Telecom"},
    {"ticker": "KOTAKBANK.NS",  "company_name": "Kotak Mahindra Bank Limited",          "exchange": "NSE", "sector": "Financial Services",           "industry": "Banks - Private Sector"},
    {"ticker": "WIPRO.NS",      "company_name": "Wipro Limited",                        "exchange": "NSE", "sector": "Information Technology",       "industry": "IT Services & Consulting"},
    {"ticker": "AXISBANK.NS",   "company_name": "Axis Bank Limited",                    "exchange": "NSE", "sector": "Financial Services",           "industry": "Banks - Private Sector"},
    {"ticker": "LTIM.NS",       "company_name": "LTIMindtree Limited",                  "exchange": "NSE", "sector": "Information Technology",       "industry": "IT Services & Consulting"},
    {"ticker": "HCLTECH.NS",    "company_name": "HCL Technologies Limited",             "exchange": "NSE", "sector": "Information Technology",       "industry": "IT Services & Consulting"},
    {"ticker": "MARUTI.NS",     "company_name": "Maruti Suzuki India Limited",          "exchange": "NSE", "sector": "Consumer Discretionary",       "industry": "Automobiles"},
    {"ticker": "SUNPHARMA.NS",  "company_name": "Sun Pharmaceutical Industries Limited","exchange": "NSE", "sector": "Healthcare",                   "industry": "Pharmaceuticals"},
    {"ticker": "TITAN.NS",      "company_name": "Titan Company Limited",                "exchange": "NSE", "sector": "Consumer Discretionary",       "industry": "Watches & Jewellery"},
    {"ticker": "NESTLEIND.NS",  "company_name": "Nestle India Limited",                 "exchange": "NSE", "sector": "Consumer Goods",               "industry": "Food Products"},
    {"ticker": "ASIANPAINT.NS", "company_name": "Asian Paints Limited",                 "exchange": "NSE", "sector": "Consumer Goods",               "industry": "Paints"},
    {"ticker": "POWERGRID.NS",  "company_name": "Power Grid Corporation of India Ltd",  "exchange": "NSE", "sector": "Utilities",                    "industry": "Electric Utilities"},
    {"ticker": "NTPC.NS",       "company_name": "NTPC Limited",                         "exchange": "NSE", "sector": "Utilities",                    "industry": "Thermal Power"},
]


async def register_companies():
    """Step 1: Register all companies via the backend API."""
    logger.info("=" * 60)
    logger.info("Step 1: Registering companies via API")
    logger.info("=" * 60)
    registered, skipped = 0, 0

    async with httpx.AsyncClient(timeout=15) as client:
        for c in COMPANIES:
            try:
                resp = await client.post(f"{API_BASE}/stocks/", json=c)
                if resp.status_code == 201:
                    logger.info("✓ Registered: %s", c["ticker"])
                    registered += 1
                elif resp.status_code == 409:
                    logger.info("→ Already exists: %s", c["ticker"])
                    skipped += 1
                else:
                    logger.error("✗ Failed %s: %d %s", c["ticker"], resp.status_code, resp.text[:100])
            except Exception as e:
                logger.error("✗ Error %s: %s", c["ticker"], e)

    logger.info("Registered: %d, Already existed: %d\n", registered, skipped)


async def seed_market_data():
    """Step 2: Fetch market data from yfinance & insert directly via asyncpg."""
    logger.info("=" * 60)
    logger.info("Step 2: Seeding market data via asyncpg (raw SQL)")
    logger.info("=" * 60)

    conn = await asyncpg.connect(DB_DSN)

    for c in COMPANIES:
        ticker = c["ticker"]
        logger.info("[%s] Fetching price data...", ticker)
        time.sleep(2)  # rate limit buffer

        try:
            yf_t = yf.Ticker(ticker)
            fi = yf_t.fast_info

            price  = getattr(fi, "last_price", None)
            mcap   = getattr(fi, "market_cap", None)
            h52    = getattr(fi, "fifty_two_week_high", None)
            l52    = getattr(fi, "fifty_two_week_low", None)
            vol    = getattr(fi, "three_month_average_volume", None)

            company_row = await conn.fetchrow(
                "SELECT id FROM companies WHERE UPPER(ticker) = UPPER($1)", ticker
            )
            if not company_row:
                logger.warning("[%s] Not in DB — skipping market data", ticker)
                continue

            cid = company_row["id"]

            await conn.execute("""
                INSERT INTO market_data (company_id, current_price, market_cap,
                    fifty_two_week_high, fifty_two_week_low, volume, last_updated)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (company_id) DO UPDATE SET
                    current_price        = EXCLUDED.current_price,
                    market_cap           = EXCLUDED.market_cap,
                    fifty_two_week_high  = EXCLUDED.fifty_two_week_high,
                    fifty_two_week_low   = EXCLUDED.fifty_two_week_low,
                    volume               = EXCLUDED.volume,
                    last_updated         = NOW()
            """,
                cid,
                float(price) if price else None,
                int(mcap) if mcap else None,
                float(h52) if h52 else None,
                float(l52) if l52 else None,
                int(vol) if vol else None,
            )
            logger.info("[%s] ✓ price=%.2f", ticker, price or 0)

        except Exception as e:
            logger.warning("[%s] Market data SKIP: %s", ticker, e)

    await conn.close()
    logger.info("Market data step done.\n")


async def seed_historical():
    """Step 3: Fetch 1y historical OHLCV via yf.download() & insert via asyncpg."""
    logger.info("=" * 60)
    logger.info("Step 3: Seeding 1y historical data via asyncpg")
    logger.info("=" * 60)

    conn = await asyncpg.connect(DB_DSN)

    for c in COMPANIES:
        ticker = c["ticker"]
        logger.info("[%s] Downloading 1y OHLCV...", ticker)
        time.sleep(2)

        try:
            company_row = await conn.fetchrow(
                "SELECT id FROM companies WHERE UPPER(ticker) = UPPER($1)", ticker
            )
            if not company_row:
                logger.warning("[%s] Not in DB — skip historical", ticker)
                continue
            cid = company_row["id"]

            # Check if already has historical data
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM historical_prices WHERE company_id=$1", cid
            )
            if count > 0:
                logger.info("[%s] Already has %d rows — skip", ticker, count)
                continue

            df = yf.download(ticker, period="1y", interval="1d",
                             auto_adjust=True, progress=False)
            if df is None or df.empty:
                logger.warning("[%s] No historical data returned", ticker)
                continue

            records = []
            for idx, row in df.iterrows():
                def sf(v):
                    try: return float(v) if v == v else None
                    except: return None
                def si(v):
                    try: return int(v) if v == v else None
                    except: return None

                # Handle MultiIndex columns from yfinance
                o = sf(row.get("Open") if not hasattr(row.get("Open"), "iloc") else row["Open"].iloc[0])
                h = sf(row.get("High") if not hasattr(row.get("High"), "iloc") else row["High"].iloc[0])
                l = sf(row.get("Low")  if not hasattr(row.get("Low"),  "iloc") else row["Low"].iloc[0])
                cl = sf(row.get("Close") if not hasattr(row.get("Close"), "iloc") else row["Close"].iloc[0])
                v = si(row.get("Volume") if not hasattr(row.get("Volume"), "iloc") else row["Volume"].iloc[0])

                records.append((
                    cid,
                    idx.date(),
                    o, h, l, cl, v
                ))

            await conn.executemany("""
                INSERT INTO historical_prices
                    (company_id, price_date, open_price, high_price, low_price, close_price, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (company_id, price_date) DO NOTHING
            """, records)

            logger.info("[%s] ✓ Inserted %d historical rows", ticker, len(records))

        except Exception as e:
            logger.warning("[%s] Historical SKIP: %s", ticker, e)

    await conn.close()
    logger.info("Historical step done.")


async def main():
    # Step 1: Register via API
    await register_companies()

    # Step 2: Market data via asyncpg
    await seed_market_data()

    # Step 3: Historical via asyncpg
    await seed_historical()

    # Final count
    logger.info("\n" + "=" * 60)
    conn = await asyncpg.connect(DB_DSN)
    companies = await conn.fetchval("SELECT COUNT(*) FROM companies")
    mdata     = await conn.fetchval("SELECT COUNT(*) FROM market_data WHERE current_price IS NOT NULL")
    hist      = await conn.fetchval("SELECT COUNT(*) FROM historical_prices")
    await conn.close()

    logger.info("FINAL DB STATE:")
    logger.info("  Companies    : %d", companies)
    logger.info("  Market data  : %d with price", mdata)
    logger.info("  Historical   : %d rows", hist)
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
