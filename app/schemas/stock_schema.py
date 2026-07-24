"""
app/schemas/stock_schema.py
============================
Pydantic schemas for stock/company API endpoints.

Response shapes match the spec exactly (Section 6.1):
{
  "ticker": "RELIANCE",
  "company_name": "Reliance Industries Ltd",
  "sector": "Energy",
  "market_data": {
    "current_price": 2945.30,
    "market_cap": 1994300000000,
    ...
  }
}
"""

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import FinPulseBaseModel


# ------------------------------------------------------------------------------
# Market data snapshot schema
# ------------------------------------------------------------------------------

class MarketDataResponse(FinPulseBaseModel):
    """Live market data snapshot for one company (maps to market_data table)."""

    current_price: Decimal | None = Field(None, examples=["2945.30"])
    market_cap: int | None = Field(None, examples=[1994300000000])
    pe_ratio: Decimal | None = Field(None, examples=["28.4"])
    eps: Decimal | None = Field(None, examples=["103.7"])
    volume: int | None = Field(None, examples=[5123400])
    fifty_two_week_high: Decimal | None = Field(None, examples=["3024.00"])
    fifty_two_week_low: Decimal | None = Field(None, examples=["2221.00"])
    dividend_yield: Decimal | None = Field(None, examples=["0.014"])
    last_updated: datetime | None = Field(None, examples=["2026-07-22T09:32:00Z"])


# ------------------------------------------------------------------------------
# Company schemas
# ------------------------------------------------------------------------------

class CompanyBase(FinPulseBaseModel):
    ticker: str = Field(..., examples=["RELIANCE.NS"])
    company_name: str = Field(..., examples=["Reliance Industries Limited"])
    exchange: str = Field(..., examples=["NSE"])
    sector: str | None = Field(None, examples=["Energy"])
    industry: str | None = Field(None, examples=["Oil & Gas Refining & Marketing"])


class CompanyCreateRequest(CompanyBase):
    """Request body for registering a new company to track."""
    pass


class CompanyResponse(CompanyBase):
    """Company info (no market data) — used in search results."""
    id: int


class StockDetailResponse(FinPulseBaseModel):
    """
    Full stock detail response — matches spec Section 6.1.

    GET /stocks/{ticker} response shape:
    {
      "ticker": "RELIANCE",
      "company_name": "Reliance Industries Ltd",
      "sector": "Energy",
      "market_data": { ... }
    }
    """

    ticker: str
    company_name: str
    exchange: str
    sector: str | None
    industry: str | None
    market_data: MarketDataResponse | None


class StockListItemResponse(FinPulseBaseModel):
    """Single item in the GET /stocks list response."""

    ticker: str
    company_name: str
    exchange: str
    sector: str | None
    current_price: Decimal | None
    market_cap: int | None
    pe_ratio: Decimal | None
    volume: int | None
    last_updated: datetime | None


class StockListResponse(FinPulseBaseModel):
    """Paginated response for GET /stocks."""

    total: int
    page: int
    page_size: int
    sector_filter: str | None
    stocks: list[StockListItemResponse]


# ------------------------------------------------------------------------------
# Comparison schema — matches spec Section 6.2
# ------------------------------------------------------------------------------

class CompareItemResponse(FinPulseBaseModel):
    """
    One company's data in a comparison response.

    GET /compare?tickers=TCS,INFY response shape:
    {
      "companies": [
        { "ticker": "TCS", "current_price": 4123.5, "pe_ratio": 30.1, "eps": 137.0 },
        { "ticker": "INFY", "current_price": 1834.2, "pe_ratio": 26.8, "eps": 68.4 }
      ]
    }
    """

    ticker: str
    company_name: str
    exchange: str
    sector: str | None
    current_price: Decimal | None
    market_cap: int | None
    pe_ratio: Decimal | None
    eps: Decimal | None
    volume: int | None
    fifty_two_week_high: Decimal | None
    fifty_two_week_low: Decimal | None
    last_updated: datetime | None


class CompareResponse(FinPulseBaseModel):
    """Full compare endpoint response."""
    companies: list[CompareItemResponse]
