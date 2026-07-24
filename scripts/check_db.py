"""scripts/check_db.py — Quick DB diagnostic"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL)

async def check():
    async with engine.connect() as conn:
        # Tables
        result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
        tables = [r[0] for r in result]
        print("Tables found:", tables)

        if "companies" not in tables:
            print("ERROR: 'companies' table does not exist! Run: python -m alembic upgrade head")
            return

        # Companies
        result = await conn.execute(text("SELECT COUNT(*) FROM companies"))
        count = result.scalar()
        print(f"Companies count: {count}")

        result = await conn.execute(text("SELECT ticker, company_name, sector FROM companies LIMIT 5"))
        for row in result:
            print(f"  - {row[0]} | {row[1]} | {row[2]}")

        # Market data
        result = await conn.execute(text("SELECT COUNT(*) FROM market_data"))
        print(f"Market data rows: {result.scalar()}")

        result = await conn.execute(text("SELECT COUNT(*) FROM market_data WHERE current_price IS NOT NULL"))
        print(f"Market data WITH price: {result.scalar()}")

        # Historical
        if "historical_prices" in tables:
            result = await conn.execute(text("SELECT COUNT(*) FROM historical_prices"))
            print(f"Historical price rows: {result.scalar()}")

    await engine.dispose()

asyncio.run(check())
