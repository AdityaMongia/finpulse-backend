"""
app/models/company.py
======================
SQLAlchemy ORM model for the `companies` table.

Stores static/slow-changing information about each tracked company.
Market data (prices, PE, etc.) lives in the separate `market_data` table.

DDL equivalent:
    CREATE TABLE companies (
        id           SERIAL PRIMARY KEY,
        ticker       VARCHAR(20) UNIQUE NOT NULL,
        company_name VARCHAR(255) NOT NULL,
        exchange     VARCHAR(10) NOT NULL,
        sector       VARCHAR(100),
        industry     VARCHAR(100),
        created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
"""

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Company(TimestampMixin, Base):
    """
    Represents a publicly listed company tracked by FinPulse.

    Relationships:
        market_data      → one-to-one  (latest snapshot, updated in place)
        historical_prices → one-to-many (daily OHLCV rows)
    """

    __tablename__ = "companies"

    __table_args__ = (
        UniqueConstraint("ticker", name="uq_companies_ticker"),
        # Index for case-insensitive name search (used by /search endpoint)
        Index("idx_companies_ticker", "ticker"),
        Index("idx_companies_exchange", "exchange"),
        Index("idx_companies_sector", "sector"),
    )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    ticker: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        doc="Stock ticker symbol, e.g. RELIANCE.NS or TCS.NS",
    )

    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Full legal company name",
    )

    exchange: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Exchange where the stock is listed: NSE or BSE",
    )

    sector: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Broad sector, e.g. Energy, Technology, Finance",
    )

    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Specific industry within the sector",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    market_data: Mapped["MarketData"] = relationship(  # type: ignore[name-defined]
        "MarketData",
        back_populates="company",
        uselist=False,          # one-to-one
        cascade="all, delete-orphan",
        lazy="select",
    )

    historical_prices: Mapped[list["HistoricalPrice"]] = relationship(  # type: ignore[name-defined]
        "HistoricalPrice",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="HistoricalPrice.date",
    )

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<Company id={self.id} ticker={self.ticker!r} exchange={self.exchange!r}>"
