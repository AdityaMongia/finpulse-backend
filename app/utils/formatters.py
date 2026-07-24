"""
app/utils/formatters.py
========================
Data formatting and conversion utilities.

Pure helper functions for formatting numbers, dates, and financial data
consistently across API responses and service logic.

These functions:
  - Have no side effects
  - Require no database or network access
  - Are safe to call from any layer (service, schemas, API)

Usage:
    from app.utils.formatters import format_currency, format_large_number

    format_currency(2750.50)           # "₹2,750.50"
    format_large_number(18620000000)   # "₹18,620.00 Cr"
    format_percentage(12.345)          # "12.35%"
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP


# ------------------------------------------------------------------------------
# Number formatting
# ------------------------------------------------------------------------------

def format_currency(value: float | Decimal | None, symbol: str = "₹") -> str:
    """
    Format a number as Indian Rupee currency string.

    Parameters
    ----------
    value : float | Decimal | None
        The numeric value to format.
    symbol : str
        Currency symbol prefix. Default: "₹"

    Returns "N/A" for None values.

    Examples:
        format_currency(2750.5)   → "₹2,750.50"
        format_currency(None)     → "N/A"
    """
    if value is None:
        return "N/A"
    decimal_value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{symbol}{decimal_value:,.2f}"


def format_large_number(value: int | float | None) -> str:
    """
    Format large numbers into human-readable Indian financial notation.

    Uses Indian numbering system: Crore (Cr) = 10M, Lakh (L) = 100K.

    Examples:
        format_large_number(18_620_000_000_000)  → "₹18,620.00 Cr Cr"
        format_large_number(18_620_000_000)      → "₹18,620.00 Cr"
        format_large_number(500_000)             → "₹5.00 L"
        format_large_number(None)                → "N/A"
    """
    if value is None:
        return "N/A"

    value = float(value)
    crore = 1_00_00_000       # 10 million
    lakh = 1_00_000           # 100 thousand

    if abs(value) >= crore:
        return f"₹{value / crore:,.2f} Cr"
    elif abs(value) >= lakh:
        return f"₹{value / lakh:,.2f} L"
    else:
        return f"₹{value:,.2f}"


def format_percentage(value: float | Decimal | None, decimals: int = 2) -> str:
    """
    Format a number as a percentage string.

    Parameters
    ----------
    value : float | Decimal | None
        The raw percentage value (e.g., 12.345 for 12.345%).
    decimals : int
        Number of decimal places to display.

    Examples:
        format_percentage(12.345)   → "12.35%"
        format_percentage(-3.2, 1) → "-3.2%"
        format_percentage(None)     → "N/A"
    """
    if value is None:
        return "N/A"
    return f"{float(value):.{decimals}f}%"


def round_decimal(value: float | Decimal | None, places: int = 2) -> Decimal | None:
    """
    Round a value to a given number of decimal places using ROUND_HALF_UP.

    Returns None if the input is None (preserves None semantics for DB fields).

    Examples:
        round_decimal(2750.5678, 2)  → Decimal("2750.57")
        round_decimal(None)           → None
    """
    if value is None:
        return None
    quantizer = Decimal(10) ** -places
    return Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP)


# ------------------------------------------------------------------------------
# Date / time formatting
# ------------------------------------------------------------------------------

def format_date(value: date | datetime | None, fmt: str = "%d %b %Y") -> str:
    """
    Format a date or datetime to a human-readable string.

    Parameters
    ----------
    value : date | datetime | None
    fmt : str
        strftime format string. Default: "15 Jan 2024"

    Examples:
        format_date(date(2024, 1, 15))          → "15 Jan 2024"
        format_date(datetime(2024, 1, 15, 9))   → "15 Jan 2024"
        format_date(None)                        → "N/A"
    """
    if value is None:
        return "N/A"
    return value.strftime(fmt)


def format_datetime_iso(value: datetime | None) -> str | None:
    """
    Format a datetime as an ISO 8601 string (UTC, with timezone).

    Used when returning timestamps in API responses for client-side parsing.

    Example:
        format_datetime_iso(datetime(2024, 1, 15, 9, 30))  → "2024-01-15T09:30:00"
    """
    if value is None:
        return None
    return value.isoformat()
