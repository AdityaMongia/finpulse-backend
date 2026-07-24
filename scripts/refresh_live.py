"""
scripts/refresh_live.py
========================
Script to immediately fetch live market data from yfinance and update
current_price, volume, and last_updated timestamps in the database.

Usage:
    cd finpulse-backend
    .\venv\Scripts\python.exe scripts/refresh_live.py
"""

import asyncio
import sys
import os
import logging

# Ensure app package is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.scheduler.jobs import refresh_live_prices, refresh_fundamentals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

async def main():
    print("Triggering immediate Market Data Refresh from yfinance...")
    try:
        await refresh_live_prices()
        print("Live market prices and timestamps updated successfully in Database!")
    except Exception as e:
        print(f"Error refreshing market data: {e}")

if __name__ == "__main__":
    asyncio.run(main())
