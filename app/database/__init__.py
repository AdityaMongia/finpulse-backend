"""
app/database/__init__.py
========================
Database infrastructure package.

Exports the three most commonly needed symbols so callers can do:
    from app.database import Base, get_db, engine
"""

from app.database.base import Base
from app.database.engine import engine
from app.database.session import get_db

__all__ = ["Base", "engine", "get_db"]
