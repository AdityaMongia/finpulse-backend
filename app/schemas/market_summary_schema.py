"""
app/schemas/market_summary_schema.py
======================================
Pydantic schema for the GET /market-summary endpoint.

This endpoint returns aggregate stats computed on read (not stored).
Spec requirement: "Computed on read, not stored"
"""

from datetime import datetime

from pydantic import Field

from app.schemas.common import FinPulseBaseModel


class MarketSummaryResponse(FinPulseBaseModel):
    """
    Aggregate market statistics across all tracked companies.

    GET /market-summary response:
    {
      "total_companies": 25,
      "avg_pe_ratio": 28.4,
      "highest_market_cap": 1994300000000,
      "highest_market_cap_ticker": "RELIANCE.NS",
      "highest_market_cap_company": "Reliance Industries Limited",
      "last_updated": "2026-07-22T09:32:00Z"
    }
    """

    total_companies: int = Field(
        ...,
        description="Total number of companies currently tracked",
        examples=[25],
    )
    avg_pe_ratio: float | None = Field(
        None,
        description="Average P/E ratio across all tracked companies (NULL-safe: excludes companies with no PE data)",
        examples=[28.4],
    )
    highest_market_cap: int | None = Field(
        None,
        description="Highest market capitalisation in INR across all tracked companies",
        examples=[1994300000000],
    )
    highest_market_cap_ticker: str | None = Field(
        None,
        description="Ticker of the company with the highest market cap",
        examples=["RELIANCE.NS"],
    )
    highest_market_cap_company: str | None = Field(
        None,
        description="Company name of the highest market cap company",
        examples=["Reliance Industries Limited"],
    )
    total_market_cap: int | None = Field(
        None,
        description="Sum of market capitalisation across tracked companies",
    )
    last_updated: datetime | None = Field(
        None,
        description="Timestamp of the most recent market data refresh",
        examples=["2026-07-22T09:32:00Z"],
    )
