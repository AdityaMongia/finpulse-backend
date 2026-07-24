"""
app/models/historical_price.py
================================
SQLAlchemy ORM model for the `historical_prices` table.

Stores daily OHLCV (Open/High/Low/Close/Volume) data for each company.
This IS an append-style time-series table — one row per company per trading day.

Critical design detail — UNIQUE(company_id, date):
    This constraint makes the daily ingestion job IDEMPOTENT.
    Running it twice on the same day:
      - Without the constraint → duplicate rows silently accumulate
      - With the constraint + ON CONFLICT DO NOTHING → safe to run multiple times

    In the defense: "I used INSERT ... ON CONFLICT DO NOTHING to make the
    historical fetch job idempotent — running it twice produces the same result
    as running it once."

DDL equivalent:
    CREATE TABLE historical_prices (
        id         SERIAL PRIMARY KEY,
        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        date       DATE NOT NULL,
        open       NUMERIC(12,2),
        high       NUMERIC(12,2),
        low        NUMERIC(12,2),
        close      NUMERIC(12,2),
        volume     BIGINT,
        UNIQUE(company_id, date)
    );
    CREATE INDEX idx_historical_company_date ON historical_prices(company_id, date);
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class HistoricalPrice(Base):
    """
    One row of OHLCV data for a company on a specific trading date.

    The UNIQUE(company_id, date) constraint is the most important line in
    this model — it prevents duplicate rows and enables idempotent ingestion.
    """

    __tablename__ = "historical_prices"

    __table_args__ = (
        UniqueConstraint("company_id", "date", name="uq_historical_company_date"),
        Index("idx_historical_company_date", "company_id", "date"),
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Trading date (market calendar date, not datetime)",
    )

    open: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Opening price at market open",
    )

    high: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Highest intraday price",
    )

    low: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Lowest intraday price",
    )

    close: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Closing price at market close",
    )

    volume: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        doc="Total shares traded on this date",
    )

    # ------------------------------------------------------------------
    # Relationship
    # ------------------------------------------------------------------

    company: Mapped["Company"] = relationship(  # type: ignore[name-defined]
        "Company",
        back_populates="historical_prices",
    )

    def __repr__(self) -> str:
        return (
            f"<HistoricalPrice company_id={self.company_id} "
            f"date={self.date} close={self.close}>"
        )
