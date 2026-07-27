"""
Market data provider for ticker symbols using yfinance.
Provides market cap, historical prices, and company fundamentals.
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
from functools import lru_cache


class MarketDataError(Exception):
    """Raised when market data cannot be fetched."""
    pass


class MarketDataCache:
    """Simple cache for market data with TTL."""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time to live for cached entries (default 5 minutes)
        """
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, key: str):
        """Get cached value if not expired."""
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl):
            del self.cache[key]
            return None

        return value

    def set(self, key: str, value):
        """Cache a value with current timestamp."""
        self.cache[key] = (value, datetime.now())

    def clear(self):
        """Clear all cached values."""
        self.cache.clear()


# Global cache instance
_market_cache = MarketDataCache()


def get_market_cap(symbol: str) -> dict:
    """
    Get market cap and basic info for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL")

    Returns:
        Dictionary with marketCap, currency, exchange, and other info.

    Raises:
        MarketDataError: If the symbol is invalid or data cannot be fetched.
    """
    cache_key = f"market_cap:{symbol.upper()}"
    cached = _market_cache.get(cache_key)
    if cached:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info:
            raise MarketDataError(f"Invalid symbol or no data available: {symbol}")

        # Get market cap, computing from shares outstanding if needed
        market_cap = info.get("marketCap") or info.get("nonDilutedMarketCap")
        if not market_cap:
            shares = info.get("sharesOutstanding")
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if shares and price:
                market_cap = shares * price
            else:
                raise MarketDataError(f"Market cap data not available for {symbol}")

        result = {
            "symbol": symbol.upper(),
            "marketCap": market_cap,
            "marketCapDisplay": _format_market_cap(market_cap),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", ""),
            "longName": info.get("longName", ""),
            "industry": info.get("industry", ""),
            "sector": info.get("sector", ""),
            "country": info.get("country", ""),
        }

        _market_cache.set(cache_key, result)
        return result

    except MarketDataError:
        raise
    except Exception as e:
        raise MarketDataError(f"Failed to fetch market cap for {symbol}: {str(e)}")


def get_historical_prices(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "daily"
) -> list[dict]:
    """
    Get historical price data for a symbol.

    Args:
        symbol: Stock ticker symbol
        start_date: Start date as "YYYY-MM-DD" (default: 1 year ago)
        end_date: End date as "YYYY-MM-DD" (default: today)
        interval: "daily", "weekly", or "monthly"

    Returns:
        List of dicts with date, open, high, low, close, volume.

    Raises:
        MarketDataError: If data cannot be fetched.
    """
    try:
        # Set default date range (1 year)
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # Map interval to yfinance period
        period_map = {
            "daily": "1d",
            "weekly": "1wk",
            "monthly": "1mo"
        }
        period = period_map.get(interval.lower(), "1d")

        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date, interval=period)

        if hist.empty:
            raise MarketDataError(f"No data available for {symbol} in date range {start_date} to {end_date}")

        prices = []
        for date, row in hist.iterrows():
            prices.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        return prices

    except Exception as e:
        raise MarketDataError(f"Failed to fetch historical prices for {symbol}: {str(e)}")


def get_company_info(symbol: str) -> dict:
    """
    Get detailed company information and fundamentals.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with PE ratio, EPS, dividend, etc.

    Raises:
        MarketDataError: If data cannot be fetched.
    """
    cache_key = f"company_info:{symbol.upper()}"
    cached = _market_cache.get(cache_key)
    if cached:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info:
            raise MarketDataError(f"Invalid symbol or data not available: {symbol}")

        result = {
            "symbol": symbol.upper(),
            "longName": info.get("longName", ""),
            "marketCap": info.get("market cap", 0),
            "marketCapDisplay": _format_market_cap(info.get("market cap", 0)),
            "currentPrice": info.get("currentPrice", 0),
            "trailingPE": info.get("trailingPE", None),
            "forwardPE": info.get("forwardPE", None),
            "trailingEPS": info.get("trailingEps", None),
            "profitMargin": info.get("profitMargins", None),
            "operatingMargin": info.get("operatingMargins", None),
            "roe": info.get("returnOnEquity", None),
            "roa": info.get("returnOnAssets", None),
            "debtToEquity": info.get("debtToEquity", None),
            "currentRatio": info.get("currentRatio", None),
            "beta": info.get("beta", None),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh", None),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow", None),
            "dividendRate": info.get("dividendRate", None),
            "dividendYield": info.get("dividendYield", None),
            "exDividendDate": _format_timestamp(info.get("exDividendDate")),
            "industry": info.get("industry", ""),
            "sector": info.get("sector", ""),
            "employees": info.get("fullTimeEmployees", None),
        }

        _market_cache.set(cache_key, result)
        return result

    except Exception as e:
        raise MarketDataError(f"Failed to fetch company info for {symbol}: {str(e)}")


def clear_cache():
    """Clear the market data cache."""
    _market_cache.clear()


def _format_market_cap(market_cap: int) -> str:
    """Format market cap as human-readable string."""
    if not market_cap:
        return "N/A"

    if market_cap >= 1e12:
        return f"${market_cap / 1e12:.2f}T"
    elif market_cap >= 1e9:
        return f"${market_cap / 1e9:.2f}B"
    elif market_cap >= 1e6:
        return f"${market_cap / 1e6:.2f}M"
    else:
        return f"${market_cap:,.0f}"


def _format_timestamp(timestamp) -> Optional[str]:
    """Convert timestamp to YYYY-MM-DD format."""
    if timestamp is None:
        return None

    if isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d")

    return None
