"""
app/models/market_data.py
==========================
SQLAlchemy ORM model for the `market_data` table.

Design decision — SNAPSHOT table (not append-only):
    One row per company, updated in place on every refresh.
    This matches the assignment's "current fundamentals" requirement.
    Historical tick data lives in `historical_prices`.

    Trade-off considered and rejected: append-only (new row per refresh)
    would enable "price changed X% in last hour" queries but grows fast
    and adds complexity not needed here.

DDL equivalent:
    CREATE TABLE market_data (
        id                  SERIAL PRIMARY KEY,
        company_id          INTEGER REFERENCES companies(id) ON DELETE CASCADE,
        current_price       NUMERIC(12,2),
        market_cap          BIGINT,
        pe_ratio            NUMERIC(10,2),
        eps                 NUMERIC(10,2),
        volume              BIGINT,
        fifty_two_week_high NUMERIC(12,2),
        fifty_two_week_low  NUMERIC(12,2),
        dividend_yield      NUMERIC(6,3),
        last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    CREATE INDEX idx_market_data_company ON market_data(company_id);
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class MarketData(Base):
    """
    Live market data snapshot for a company.

    Updated in place by the `refresh_live_prices` and `refresh_fundamentals`
    scheduler jobs. One row per company — not a time-series table.

    Note: Does NOT use TimestampMixin because `last_updated` has a specific
    financial meaning (last market data fetch timestamp) distinct from generic
    created_at/updated_at audit columns.
    """

    __tablename__ = "market_data"

    __table_args__ = (
        Index("idx_market_data_company", "company_id"),
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,        # enforces one-to-one with Company
        index=True,
    )

    current_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Latest traded price in INR",
    )

    market_cap: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        doc="Market capitalisation in INR (price × shares outstanding)",
    )

    pe_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Price-to-Earnings ratio",
    )

    eps: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Earnings Per Share in INR",
    )

    volume: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        doc="Trading volume (number of shares traded today)",
    )

    fifty_two_week_high: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Highest price in the last 52 weeks",
    )

    fifty_two_week_low: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Lowest price in the last 52 weeks",
    )

    dividend_yield: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3),
        nullable=True,
        doc="Annual dividend yield as a decimal (0.014 = 1.4%)",
    )

    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
        doc="Timestamp of the last successful market data fetch from yFinance",
    )

    # ------------------------------------------------------------------
    # Relationship
    # ------------------------------------------------------------------

    company: Mapped["Company"] = relationship(  # type: ignore[name-defined]
        "Company",
        back_populates="market_data",
    )

    def __repr__(self) -> str:
        return (
            f"<MarketData company_id={self.company_id} "
            f"price={self.current_price} last_updated={self.last_updated}>"
        )
