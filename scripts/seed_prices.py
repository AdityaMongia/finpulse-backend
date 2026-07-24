"""scripts/seed_prices.py - Insert approximate market data directly via asyncpg."""
import asyncio
import asyncpg

DB_DSN = "postgresql://finpulse:finpulse_secret@localhost:5434/finpulse_db"

# Approximate NSE data (July 2026) — will be overwritten when yfinance rate-limit resets
MARKET_DATA = {
    "RELIANCE.NS":   {"price": 1485.50, "mcap": 2_06_81_40_00_00_000, "pe": 28.4, "eps": 52.3, "vol": 12_800_000, "h52": 1608.0, "l52": 1201.0},
    "TCS.NS":        {"price": 4105.00, "mcap": 1_49_40_00_00_00_000, "pe": 33.1, "eps": 124.0,"vol":  3_200_000, "h52": 4592.0, "l52": 3311.0},
    "INFY.NS":       {"price": 1892.00, "mcap":  78_90_00_00_00_000,  "pe": 25.6, "eps": 73.9, "vol":  8_500_000, "h52": 2006.0, "l52": 1351.0},
    "HDFCBANK.NS":   {"price": 1952.00, "mcap": 1_48_60_00_00_00_000, "pe": 18.2, "eps": 107.3,"vol": 14_600_000, "h52": 1978.0, "l52": 1363.0},
    "ICICIBANK.NS":  {"price": 1452.00, "mcap": 1_02_30_00_00_00_000, "pe": 19.8, "eps": 73.4, "vol": 18_200_000, "h52": 1478.0, "l52":  942.0},
    "HINDUNILVR.NS": {"price": 2648.00, "mcap":  62_14_00_00_00_000,  "pe": 55.3, "eps": 47.9, "vol":  1_800_000, "h52": 2980.0, "l52": 2172.0},
    "SBIN.NS":       {"price":  822.00, "mcap":  73_35_00_00_00_000,  "pe": 12.1, "eps": 67.9, "vol": 28_400_000, "h52":  912.0, "l52":  600.0},
    "BHARTIARTL.NS": {"price": 1935.00, "mcap": 1_14_80_00_00_00_000, "pe": 82.0, "eps": 23.6, "vol":  5_600_000, "h52": 1998.0, "l52": 1269.0},
    "KOTAKBANK.NS":  {"price": 2198.00, "mcap":  43_85_00_00_00_000,  "pe": 22.4, "eps": 98.1, "vol":  4_100_000, "h52": 2234.0, "l52": 1543.0},
    "WIPRO.NS":      {"price":  531.00, "mcap":  27_95_00_00_00_000,  "pe": 26.1, "eps": 20.4, "vol":  7_200_000, "h52":  598.0, "l52":  415.0},
    "AXISBANK.NS":   {"price": 1248.00, "mcap":  38_54_00_00_00_000,  "pe": 14.9, "eps": 83.8, "vol": 10_200_000, "h52": 1340.0, "l52":  953.0},
    "LTIM.NS":       {"price": 6512.00, "mcap":  19_25_00_00_00_000,  "pe": 35.6, "eps": 182.9,"vol":    640_000, "h52": 7194.0, "l52": 4901.0},
    "HCLTECH.NS":    {"price": 1802.00, "mcap":  48_99_00_00_00_000,  "pe": 28.3, "eps": 63.7, "vol":  3_800_000, "h52": 2012.0, "l52": 1235.0},
    "MARUTI.NS":     {"price": 13490.00,"mcap":  40_78_00_00_00_000,  "pe": 30.2, "eps": 447.0,"vol":    380_000, "h52": 13680.0,"l52": 9832.0},
    "SUNPHARMA.NS":  {"price": 1792.00, "mcap":  43_06_00_00_00_000,  "pe": 38.1, "eps": 47.0, "vol":  3_100_000, "h52": 1960.0, "l52": 1210.0},
    "TITAN.NS":      {"price": 3598.00, "mcap":  31_98_00_00_00_000,  "pe": 92.0, "eps": 39.1, "vol":  1_400_000, "h52": 3899.0, "l52": 2860.0},
    "NESTLEIND.NS":  {"price": 2452.00, "mcap":  23_61_00_00_00_000,  "pe": 68.4, "eps": 35.8, "vol":    420_000, "h52": 2778.0, "l52": 2100.0},
    "ASIANPAINT.NS": {"price": 2382.00, "mcap":  22_82_00_00_00_000,  "pe": 55.1, "eps": 43.2, "vol":  1_100_000, "h52": 3282.0, "l52": 2025.0},
    "POWERGRID.NS":  {"price":  326.00, "mcap":  30_32_00_00_00_000,  "pe": 16.3, "eps": 20.0, "vol":  9_800_000, "h52":  366.0, "l52":  222.0},
    "NTPC.NS":       {"price":  358.00, "mcap":  34_76_00_00_00_000,  "pe": 18.1, "eps": 19.8, "vol": 12_500_000, "h52":  407.0, "l52":  252.0},
}

async def main():
    conn = await asyncpg.connect(DB_DSN)
    ok = 0
    for ticker, d in MARKET_DATA.items():
        row = await conn.fetchrow("SELECT id FROM companies WHERE UPPER(ticker)=UPPER($1)", ticker)
        if not row:
            print(f"  SKIP {ticker} — not in companies table")
            continue
        cid = row["id"]
        await conn.execute("""
            INSERT INTO market_data
                (company_id, current_price, market_cap, pe_ratio, eps,
                 volume, fifty_two_week_high, fifty_two_week_low, last_updated)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NOW())
            ON CONFLICT (company_id) DO UPDATE SET
                current_price       = EXCLUDED.current_price,
                market_cap          = EXCLUDED.market_cap,
                pe_ratio            = EXCLUDED.pe_ratio,
                eps                 = EXCLUDED.eps,
                volume              = EXCLUDED.volume,
                fifty_two_week_high = EXCLUDED.fifty_two_week_high,
                fifty_two_week_low  = EXCLUDED.fifty_two_week_low,
                last_updated        = NOW()
        """, cid, d["price"], d["mcap"], d["pe"], d["eps"], d["vol"], d["h52"], d["l52"])
        print(f"  OK {ticker}  Rs{d['price']}")
        ok += 1

    await conn.close()
    print(f"\nDone: {ok} tickers updated with approximate market data.")
    print("NOTE: These are approximate values -- real data will load once yfinance rate-limit resets.")

asyncio.run(main())
