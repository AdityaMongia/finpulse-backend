"""
app/database/base.py
=====================
SQLAlchemy declarative base and shared column mixins.

All ORM model classes in `app/models/` MUST inherit from `Base`.
This ensures Alembic can auto-detect models during `alembic revision --autogenerate`.

Mixins
------
TimestampMixin:
    Adds `created_at` and `updated_at` columns to any model that inherits it.
    `updated_at` is automatically refreshed on every UPDATE via `onupdate`.

Usage (in app/models/your_model.py):
    from app.database.base import Base, TimestampMixin
    from sqlalchemy.orm import Mapped, mapped_column

    class Company(TimestampMixin, Base):
        __tablename__ = "companies"
        id: Mapped[int] = mapped_column(primary_key=True)
        ticker: Mapped[str] = mapped_column(unique=True)
        ...
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Shared declarative base for all SQLAlchemy ORM models.

    Using a single Base means:
      - Alembic autogenerate can discover all models by importing Base
      - Table metadata is shared across the whole application
      - No risk of "table already defined" errors from multiple bases
    """
    pass


class TimestampMixin:
    """
    Mixin that adds `created_at` and `updated_at` audit columns.

    Both columns use the database server's `NOW()` function (via `func.now()`),
    so timestamps are consistent even if the application server's clock drifts.

    Columns:
        created_at: Set once when the row is first inserted. Never updated.
        updated_at: Set on insert AND automatically refreshed on every UPDATE.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp of record creation (set by DB server, never changed).",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),  # Automatically updated on every SQL UPDATE
        nullable=False,
        doc="Timestamp of last record modification (auto-updated by DB server).",
    )
