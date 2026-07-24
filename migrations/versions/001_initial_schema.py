"""Initial schema: companies, market_data, historical_prices

Revision ID: 001
Revises:
Create Date: 2026-07-22 00:00:00.000000

Creates the three core tables for FinPulse:
  1. companies          — static company info
  2. market_data        — live market snapshot (one row per company)
  3. historical_prices  — daily OHLCV time-series

Key design decisions captured here:
  - market_data uses UNIQUE(company_id) to enforce one-row-per-company
  - historical_prices uses UNIQUE(company_id, date) for idempotent ingestion
  - All foreign keys use ON DELETE CASCADE (removing a company removes all its data)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables, indexes, and constraints."""

    # ------------------------------------------------------------------
    # 1. companies
    # ------------------------------------------------------------------
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", name="uq_companies_ticker"),
    )
    op.create_index("idx_companies_ticker", "companies", ["ticker"])
    op.create_index("idx_companies_exchange", "companies", ["exchange"])
    op.create_index("idx_companies_sector", "companies", ["sector"])

    # ------------------------------------------------------------------
    # 2. market_data  (snapshot: one row per company, updated in place)
    # ------------------------------------------------------------------
    op.create_table(
        "market_data",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.Column("pe_ratio", sa.Numeric(10, 2), nullable=True),
        sa.Column("eps", sa.Numeric(10, 2), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("fifty_two_week_high", sa.Numeric(12, 2), nullable=True),
        sa.Column("fifty_two_week_low", sa.Numeric(12, 2), nullable=True),
        sa.Column("dividend_yield", sa.Numeric(6, 3), nullable=True),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_market_data_company"),
    )
    op.create_index("idx_market_data_company", "market_data", ["company_id"])

    # ------------------------------------------------------------------
    # 3. historical_prices  (time-series: one row per company per date)
    # ------------------------------------------------------------------
    op.create_table(
        "historical_prices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(12, 2), nullable=True),
        sa.Column("high", sa.Numeric(12, 2), nullable=True),
        sa.Column("low", sa.Numeric(12, 2), nullable=True),
        sa.Column("close", sa.Numeric(12, 2), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        # THE most important constraint: prevents duplicate rows on re-fetch
        # Enables: INSERT ... ON CONFLICT (company_id, date) DO NOTHING
        sa.UniqueConstraint(
            "company_id", "date", name="uq_historical_company_date"
        ),
    )
    op.create_index(
        "idx_historical_company_date",
        "historical_prices",
        ["company_id", "date"],
    )


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("historical_prices")
    op.drop_table("market_data")
    op.drop_table("companies")
