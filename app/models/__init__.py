"""
app/models/__init__.py
======================
ORM model package.

All model classes are imported here so Alembic's `env.py` can discover
them via Base.metadata when running `alembic revision --autogenerate`.

Import order matters: Company must be imported before MarketData and
HistoricalPrice because they reference Company via ForeignKey.
"""

from app.models.company import Company
from app.models.historical_price import HistoricalPrice
from app.models.market_data import MarketData

__all__: list[str] = ["Company", "MarketData", "HistoricalPrice"]
