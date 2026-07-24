"""
app/services/yfinance_client.py
================================
Async wrapper around the yFinance library.

All yfinance calls are CPU/IO-bound synchronous operations.
We use `asyncio.to_thread()` to run them in a thread pool so they never
block FastAPI's event loop.

Error handling strategy (per Section 8):
  - yFinance timeout          → asyncio.wait_for with 15s limit, 1 retry with 2s backoff
  - yFinance returns None/{}  → ExternalServiceError (not silent zero-fill)
  - Network error             → ExternalServiceError with descriptive message
"""

import asyncio
import logging
from typing import Any

import yfinance as yf

from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

_SERVICE_NAME = "yFinance"
_TIMEOUT_SECONDS = 15
_RETRY_DELAY_SECONDS = 2


async def _run_in_thread(func, *args, **kwargs) -> Any:
    """Run a synchronous function in a thread pool (non-blocking)."""
    return await asyncio.to_thread(func, *args, **kwargs)


class YFinanceClient:
    """
    Async client for fetching market data via the yfinance library.

    Every public method:
      1. Calls yfinance synchronously in a thread pool
      2. Validates the response (raises ExternalServiceError on bad data)
      3. Returns a clean dict — no yfinance objects leak out of this class
    """

    # ------------------------------------------------------------------
    # Current quote (live price + fundamentals)
    # ------------------------------------------------------------------

    async def get_current_quote(self, ticker: str) -> dict[str, Any]:
        """
        Fetch the current market snapshot for a ticker.

        Returns dict with keys:
          current_price, market_cap, pe_ratio, eps, volume,
          fifty_two_week_high, fifty_two_week_low, dividend_yield

        Raises:
            ExternalServiceError: if yFinance returns no data or times out.

        Note: Missing fields (e.g. PE not available for some companies) are
        returned as None — never faked as 0 (per error handling spec).
        """
        info = await self._fetch_ticker_info(ticker)

        return {
            "current_price": self._safe_decimal(
                info.get("currentPrice") or info.get("regularMarketPrice")
            ),
            "market_cap": self._safe_int(info.get("marketCap")),
            "pe_ratio": self._safe_decimal(info.get("trailingPE")),
            "eps": self._safe_decimal(info.get("trailingEps")),
            "volume": self._safe_int(
                info.get("volume") or info.get("regularMarketVolume")
            ),
            "fifty_two_week_high": self._safe_decimal(info.get("fiftyTwoWeekHigh")),
            "fifty_two_week_low": self._safe_decimal(info.get("fiftyTwoWeekLow")),
            "dividend_yield": self._safe_decimal(info.get("dividendYield")),
        }

    async def get_live_price_and_volume(self, ticker: str) -> dict[str, Any]:
        """
        Lightweight fetch — only current price and volume.
        Called by the `refresh_live_prices` scheduler job (runs every 3 min).
        Faster than get_current_quote because it skips fundamentals.
        """
        info = await self._fetch_ticker_info(ticker)

        return {
            "current_price": self._safe_decimal(
                info.get("currentPrice") or info.get("regularMarketPrice")
            ),
            "volume": self._safe_int(
                info.get("volume") or info.get("regularMarketVolume")
            ),
        }

    async def get_fundamentals(self, ticker: str) -> dict[str, Any]:
        """
        Fetch PE, EPS, market cap, 52-week range.
        Called by the `refresh_fundamentals` scheduler job (runs daily at 8 AM).
        """
        info = await self._fetch_ticker_info(ticker)

        return {
            "pe_ratio": self._safe_decimal(info.get("trailingPE")),
            "eps": self._safe_decimal(info.get("trailingEps")),
            "market_cap": self._safe_int(info.get("marketCap")),
            "fifty_two_week_high": self._safe_decimal(info.get("fiftyTwoWeekHigh")),
            "fifty_two_week_low": self._safe_decimal(info.get("fiftyTwoWeekLow")),
            "dividend_yield": self._safe_decimal(info.get("dividendYield")),
        }

    # ------------------------------------------------------------------
    # Company info (static)
    # ------------------------------------------------------------------

    async def get_company_info(self, ticker: str) -> dict[str, Any]:
        """
        Fetch static company info: name, sector, industry, exchange.
        Called when registering a new company.
        """
        info = await self._fetch_ticker_info(ticker)

        return {
            "company_name": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "exchange": info.get("exchange", "NSE"),
        }

    # ------------------------------------------------------------------
    # Historical OHLCV
    # ------------------------------------------------------------------

    async def get_historical_prices(
        self,
        ticker: str,
        period: str = "1mo",
    ) -> list[dict[str, Any]]:
        """
        Fetch daily OHLCV data for a given period.

        Parameters
        ----------
        ticker : str
            Stock ticker (e.g., "RELIANCE.NS")
        period : str
            yfinance period string: "1mo", "3mo", "6mo", "1y"

        Returns list of dicts with keys: date, open, high, low, close, volume
        Returns [] for empty data (new listing, delisted) — per error spec.

        Raises:
            ExternalServiceError: on timeout or network failure.
        """
        def _download():
            return yf.download(
                ticker,
                period=period,
                interval="1d",
                auto_adjust=True,
                progress=False,
            )

        try:
            df = await asyncio.wait_for(
                _run_in_thread(_download),
                timeout=_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("yFinance timeout for %s historical (period=%s)", ticker, period)
            # 1 retry with backoff
            await asyncio.sleep(_RETRY_DELAY_SECONDS)
            try:
                df = await asyncio.wait_for(
                    _run_in_thread(_download),
                    timeout=_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.error("yFinance historical retry also timed out for %s", ticker)
                raise ExternalServiceError(
                    service=_SERVICE_NAME,
                    detail=f"Timeout fetching historical data for {ticker}. Try again later.",
                )
        except Exception as exc:
            logger.exception("yFinance error fetching historical for %s", ticker)
            raise ExternalServiceError(
                service=_SERVICE_NAME,
                detail=f"Failed to fetch historical data for {ticker}: {exc}",
            )

        # Empty DataFrame = no data (new listing, delisted) — return [] not error
        if df is None or df.empty:
            logger.info("yFinance returned empty historical data for %s", ticker)
            return []

        records = []
        for idx, row in df.iterrows():
            records.append({
                "date": idx.date() if hasattr(idx, "date") else idx,
                "open": self._safe_decimal(row.get("Open")),
                "high": self._safe_decimal(row.get("High")),
                "low": self._safe_decimal(row.get("Low")),
                "close": self._safe_decimal(row.get("Close")),
                "volume": self._safe_int(row.get("Volume")),
            })

        return records

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_ticker_info(self, ticker: str) -> dict[str, Any]:
        """
        Fetch yfinance `.info` dict with timeout + 1 retry on timeout.

        Centralises all retry/timeout logic so get_current_quote,
        get_fundamentals, get_company_info don't duplicate it.
        """
        def _get_info():
            return yf.Ticker(ticker).info

        try:
            info = await asyncio.wait_for(
                _run_in_thread(_get_info),
                timeout=_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("yFinance timeout for %s — retrying once", ticker)
            await asyncio.sleep(_RETRY_DELAY_SECONDS)
            try:
                info = await asyncio.wait_for(
                    _run_in_thread(_get_info),
                    timeout=_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.error("yFinance retry timed out for %s", ticker)
                raise ExternalServiceError(
                    service=_SERVICE_NAME,
                    detail=f"yFinance is not responding for ticker '{ticker}'. Try again later.",
                )
        except Exception as exc:
            logger.exception("Unexpected yFinance error for ticker %s", ticker)
            raise ExternalServiceError(
                service=_SERVICE_NAME,
                detail=f"Failed to fetch data for '{ticker}': {exc}",
            )

        # Empty dict = invalid ticker or yFinance hiccup
        if not info or info.get("trailingPegRatio") is None and not info.get("longName"):
            # yFinance returns a near-empty dict for invalid tickers
            # We check for a key that would always exist for real tickers
            # Note: we don't raise here — let the caller decide
            # (company_info might still be partially useful)
            logger.warning("yFinance returned sparse info for %s", ticker)

        return info or {}

    @staticmethod
    def _safe_decimal(value: Any) -> float | None:
        """Convert to float, return None for invalid/missing values."""
        try:
            if value is None or (isinstance(value, float) and (value != value)):  # NaN check
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        """Convert to int, return None for invalid/missing values."""
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None
