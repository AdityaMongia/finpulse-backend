"""scripts/seed_historical_synthetic.py
Generate ~365 days of synthetic OHLCV data for each stock
using a random walk seeded from the approximate current price.
This gives working charts while yfinance rate-limit recovers.
"""
import asyncio
import asyncpg
import random
import datetime

import os
DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/finpulse_db").replace("postgresql+asyncpg://", "postgresql://")

BASE_PRICES = {
    "RELIANCE.NS": 1485.50, "TCS.NS": 4105.00, "INFY.NS": 1892.00,
    "HDFCBANK.NS": 1952.00, "ICICIBANK.NS": 1452.00, "HINDUNILVR.NS": 2648.00,
    "SBIN.NS": 822.00, "BHARTIARTL.NS": 1935.00, "KOTAKBANK.NS": 2198.00,
    "WIPRO.NS": 531.00, "AXISBANK.NS": 1248.00, "LTIM.NS": 6512.00,
    "HCLTECH.NS": 1802.00, "MARUTI.NS": 13490.00, "SUNPHARMA.NS": 1792.00,
    "TITAN.NS": 3598.00, "NESTLEIND.NS": 2452.00, "ASIANPAINT.NS": 2382.00,
    "POWERGRID.NS": 326.00, "NTPC.NS": 358.00,
}

def generate_ohlcv(base_price: float, days: int = 365):
    """Backward-looking random walk from today's price."""
    records = []
    price = base_price
    today = datetime.date.today()

    # Walk backwards
    for i in range(days, 0, -1):
        date = today - datetime.timedelta(days=i)
        # Skip weekends
        if date.weekday() >= 5:
            continue

        daily_change = random.gauss(0.0003, 0.015)   # slight upward drift
        open_p  = price
        close_p = round(price * (1 + daily_change), 2)
        high_p  = round(max(open_p, close_p) * (1 + abs(random.gauss(0, 0.005))), 2)
        low_p   = round(min(open_p, close_p) * (1 - abs(random.gauss(0, 0.005))), 2)
        volume  = int(random.uniform(500_000, 20_000_000))

        records.append((date, open_p, high_p, low_p, close_p, volume))
        price = close_p

    return records


async def main():
    random.seed(42)  # reproducible
    conn = await asyncpg.connect(DB_DSN)

    total = 0
    for ticker, base_price in BASE_PRICES.items():
        row = await conn.fetchrow("SELECT id FROM companies WHERE UPPER(ticker)=UPPER($1)", ticker)
        if not row:
            print(f"SKIP {ticker}")
            continue
        cid = row["id"]

        # Check existing
        count = await conn.fetchval("SELECT COUNT(*) FROM historical_prices WHERE company_id=$1", cid)
        if count > 0:
            print(f"SKIP {ticker} - already has {count} rows")
            continue

        ohlcv = generate_ohlcv(base_price)
        records = [(cid, d, o, h, l, c, v) for (d, o, h, l, c, v) in ohlcv]

        await conn.executemany("""
            INSERT INTO historical_prices
                (company_id, date, open, high, low, close, volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (company_id, date) DO NOTHING
        """, records)

        print(f"  OK {ticker}  {len(records)} synthetic days")
        total += len(records)

    await conn.close()
    print(f"\nDone: {total} total historical rows inserted (synthetic).")
    print("NOTE: Real historical data will replace this when yfinance rate-limit resets.")

asyncio.run(main())
