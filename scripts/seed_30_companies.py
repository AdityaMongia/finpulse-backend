"""
scripts/seed_30_companies.py
=============================
Register and seed market data for the exact 30 specified Indian companies.
"""

import asyncio
import os
import sys
import logging
import yfinance as yf
from decimal import Decimal

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.config import settings
from app.repositories.company_repository import CompanyRepository
from app.repositories.market_data_repository import MarketDataRepository
from app.repositories.historical_price_repository import HistoricalPriceRepository
from app.services.yfinance_client import YFinanceClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_30")

# 30 Specific Companies requested by user
TARGET_COMPANIES = [
    {"ticker": "RELIANCE.NS",   "company_name": "Reliance Industries Limited",          "exchange": "NSE", "sector": "Energy",                 "industry": "Oil & Gas Refining & Marketing"},
    {"ticker": "HDFCBANK.NS",   "company_name": "HDFC Bank Limited",                    "exchange": "NSE", "sector": "Financial Services",      "industry": "Banks - Private Sector"},
    {"ticker": "ICICIBANK.NS",  "company_name": "ICICI Bank Limited",                   "exchange": "NSE", "sector": "Financial Services",      "industry": "Banks - Private Sector"},
    {"ticker": "SBIN.NS",       "company_name": "State Bank of India",                  "exchange": "NSE", "sector": "Financial Services",      "industry": "Banks - Public Sector"},
    {"ticker": "TCS.NS",        "company_name": "Tata Consultancy Services Limited",    "exchange": "NSE", "sector": "Information Technology",  "industry": "IT Services & Consulting"},
    {"ticker": "INFY.NS",       "company_name": "Infosys Limited",                      "exchange": "NSE", "sector": "Information Technology",  "industry": "IT Services & Consulting"},
    {"ticker": "BHARTIARTL.NS", "company_name": "Bharti Airtel Limited",                "exchange": "NSE", "sector": "Communication Services",  "industry": "Telecom"},
    {"ticker": "LT.NS",         "company_name": "Larsen & Toubro Limited",              "exchange": "NSE", "sector": "Industrials",             "industry": "Engineering & Construction"},
    {"ticker": "MARUTI.NS",     "company_name": "Maruti Suzuki India Limited",          "exchange": "NSE", "sector": "Consumer Discretionary",  "industry": "Automobiles"},
    {"ticker": "M&M.NS",        "company_name": "Mahindra & Mahindra Limited",          "exchange": "NSE", "sector": "Consumer Discretionary",  "industry": "Automobiles"},
    {"ticker": "TATAMOTORS.NS", "company_name": "Tata Motors Limited",                  "exchange": "NSE", "sector": "Consumer Discretionary",  "industry": "Automobiles"},
    {"ticker": "HINDUNILVR.NS", "company_name": "Hindustan Unilever Limited",           "exchange": "NSE", "sector": "Consumer Goods",          "industry": "FMCG"},
    {"ticker": "ITC.NS",        "company_name": "ITC Limited",                          "exchange": "NSE", "sector": "Consumer Goods",          "industry": "FMCG & Tobacco"},
    {"ticker": "TITAN.NS",      "company_name": "Titan Company Limited",                "exchange": "NSE", "sector": "Consumer Discretionary",  "industry": "Watches & Jewellery"},
    {"ticker": "SUNPHARMA.NS",  "company_name": "Sun Pharmaceutical Industries Limited","exchange": "NSE", "sector": "Healthcare",              "industry": "Pharmaceuticals"},
    {"ticker": "ULTRACEMCO.NS", "company_name": "UltraTech Cement Limited",             "exchange": "NSE", "sector": "Materials",               "industry": "Cement & Building Materials"},
    {"ticker": "YATHARTH.NS",   "company_name": "Yatharth Hospital and Trauma Care Services Limited", "exchange": "NSE", "sector": "Healthcare", "industry": "Healthcare Services"},
    {"ticker": "ZENTEC.NS",     "company_name": "Zen Technologies Limited",             "exchange": "NSE", "sector": "Industrials",             "industry": "Aerospace & Defense"},
    {"ticker": "NETWEB.NS",     "company_name": "Netweb Technologies India Limited",    "exchange": "NSE", "sector": "Information Technology",  "industry": "IT Infrastructure & Hardware"},
    {"ticker": "NTPCGREEN.NS",  "company_name": "NTPC Green Energy Limited",            "exchange": "NSE", "sector": "Utilities",               "industry": "Renewable Energy"},
    {"ticker": "ADANIGREEN.NS", "company_name": "Adani Green Energy Limited",           "exchange": "NSE", "sector": "Utilities",               "industry": "Renewable Energy"},
    {"ticker": "ADANIPORTS.NS", "company_name": "Adani Ports and Special Economic Zone", "exchange": "NSE", "sector": "Industrials",            "industry": "Ports & Logistics"},
    {"ticker": "COALINDIA.NS",  "company_name": "Coal India Limited",                   "exchange": "NSE", "sector": "Energy",                 "industry": "Mining & Coal"},
    {"ticker": "BAJFINANCE.NS", "company_name": "Bajaj Finance Limited",                "exchange": "NSE", "sector": "Financial Services",      "industry": "NBFC & Financial Services"},
    {"ticker": "ASTRAL.NS",     "company_name": "Astral Limited",                       "exchange": "NSE", "sector": "Industrials",             "industry": "Building Products & Pipes"},
    {"ticker": "JIOFIN.NS",     "company_name": "Jio Financial Services Limited",        "exchange": "NSE", "sector": "Financial Services",      "industry": "Financial Services"},
    {"ticker": "MARICO.NS",     "company_name": "Marico Limited",                       "exchange": "NSE", "sector": "Consumer Goods",          "industry": "FMCG"},
    {"ticker": "TRENT.NS",      "company_name": "Trent Limited",                        "exchange": "NSE", "sector": "Consumer Discretionary",  "industry": "Retail & Fashion"},
    {"ticker": "NYKAA.NS",      "company_name": "FSN E-Commerce Ventures Limited (Nykaa)", "exchange": "NSE", "sector": "Consumer Discretionary","industry": "E-Commerce & Beauty"},
    {"ticker": "ONGC.NS",       "company_name": "Oil & Natural Gas Corporation Limited", "exchange": "NSE", "sector": "Energy",                 "industry": "Oil & Gas Exploration"},
]

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

yf_client = YFinanceClient()


async def seed():
    async with AsyncSessionLocal() as session:
        company_repo = CompanyRepository(session)
        market_repo = MarketDataRepository(session)

        # 1. Register companies if not already present
        registered_count = 0
        for comp in TARGET_COMPANIES:
            existing = await company_repo.get_by_ticker(comp["ticker"])
            if not existing:
                logger.info("Registering company: %s (%s)", comp["company_name"], comp["ticker"])
                try:
                    c = await company_repo.create(
                        ticker=comp["ticker"],
                        company_name=comp["company_name"],
                        exchange=comp["exchange"],
                        sector=comp["sector"],
                        industry=comp["industry"],
                    )
                    registered_count += 1
                except Exception as e:
                    logger.error("Error registering %s: %s", comp["ticker"], e)

        await session.commit()
        logger.info("Registered %d new companies.", registered_count)

        # 2. Fetch live quote / market data for each ticker from yFinance and upsert
        all_companies = await company_repo.get_all_with_market_data(offset=0, limit=100)
        logger.info("Total companies in DB: %d", len(all_companies))

        for comp in all_companies:
            logger.info("Fetching market data for %s...", comp.ticker)
            try:
                # Try fetching quote via yfinance
                yf_t = yf.Ticker(comp.ticker)
                fi = yf_t.fast_info
                
                price = getattr(fi, "last_price", None) or getattr(fi, "previous_close", None)
                mcap = getattr(fi, "market_cap", None)
                h52 = getattr(fi, "fifty_two_week_high", None)
                l52 = getattr(fi, "fifty_two_week_low", None)
                vol = getattr(fi, "three_month_average_volume", None) or getattr(fi, "last_volume", None)
                
                # Fetch basic summary detail if possible
                pe = None
                eps = None
                try:
                    info = yf_t.info
                    pe = info.get("trailingPE") or info.get("forwardPE")
                    eps = info.get("trailingEps")
                    if not price:
                        price = info.get("currentPrice") or info.get("regularMarketPrice")
                    if not mcap:
                        mcap = info.get("marketCap")
                except Exception:
                    pass

                if price:
                    p_dec = Decimal(str(round(price, 2)))
                    mcap_int = int(mcap) if mcap else None
                    pe_dec = Decimal(str(round(pe, 2))) if pe else None
                    eps_dec = Decimal(str(round(eps, 2))) if eps else None
                    h52_dec = Decimal(str(round(h52, 2))) if h52 else None
                    l52_dec = Decimal(str(round(l52, 2))) if l52 else None
                    vol_int = int(vol) if vol else None

                    await market_repo.upsert(
                        company_id=comp.id,
                        current_price=p_dec,
                        market_cap=mcap_int,
                        pe_ratio=pe_dec,
                        eps=eps_dec,
                        volume=vol_int,
                        fifty_two_week_high=h52_dec,
                        fifty_two_week_low=l52_dec,
                    )
                    logger.info("✓ %s updated: price=₹%.2f, mcap=%s, pe=%s", comp.ticker, price, mcap, pe)
                else:
                    logger.warning("✗ Could not get price for %s", comp.ticker)
            except Exception as e:
                logger.error("Error updating %s: %s", comp.ticker, e)

        await session.commit()

        # Check total count in DB
        result = await session.execute(text("SELECT COUNT(*) FROM companies"))
        total = result.scalar()
        logger.info("Seeding complete! Total companies in database now: %d", total)

if __name__ == "__main__":
    asyncio.run(seed())
