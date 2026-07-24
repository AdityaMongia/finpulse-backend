"""
app/schemas/historical_schema.py
=================================
Pydantic schemas for historical price data API endpoints.

Defines request/response shapes for OHLCV data.
"""

import datetime as dt
from decimal import Decimal

from pydantic import Field, field_validator

from app.schemas.common import FinPulseBaseModel


# ------------------------------------------------------------------------------
# Historical price record
# ------------------------------------------------------------------------------

class HistoricalPriceRecord(FinPulseBaseModel):
    """A single row of OHLCV data for one trading day."""

    # Use aliased import to avoid shadowing built-in `date`
    price_date: dt.date = Field(..., alias="date", description="Trading date (YYYY-MM-DD)")
    open_price: Decimal | None = Field(None, alias="open", examples=["2710.25"])
    high_price: Decimal | None = Field(None, alias="high", examples=["2780.00"])
    low_price: Decimal | None = Field(None, alias="low", examples=["2695.50"])
    close_price: Decimal | None = Field(None, alias="close", examples=["2765.80"])
    volume: int | None = Field(None, examples=[5241089])

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,   # allow both field name and alias
    }


# ------------------------------------------------------------------------------
# Request / query parameter schemas
# ------------------------------------------------------------------------------

class HistoricalPriceQueryParams(FinPulseBaseModel):
    """Query parameters for the historical price endpoint."""

    start_date: dt.date = Field(..., description="Start date (inclusive)")
    end_date: dt.date = Field(..., description="End date (inclusive)")

    @field_validator("end_date")
    @classmethod
    def end_date_after_start_date(cls, end_date: dt.date, info) -> dt.date:
        start_date = info.data.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        return end_date


# ------------------------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------------------------

class HistoricalPriceResponse(FinPulseBaseModel):
    """
    Response for historical OHLCV data.
    range field renamed to date_range to avoid shadowing Python built-in.
    """

    ticker: str = Field(..., examples=["RELIANCE.NS"])
    company_name: str = Field(..., examples=["Reliance Industries Limited"])
    date_range: str = Field(
        ...,
        alias="range",
        examples=["3m"],
        description="Requested range: 1m/3m/6m/1y",
    )
    total_records: int = Field(..., description="Number of records returned")
    prices: list[HistoricalPriceRecord] = Field(
        ..., description="OHLCV records ordered by date ascending"
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }
