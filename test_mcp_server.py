#!/usr/bin/env python3
"""
Quick test script for the Schwab MCP server.
Verifies that all market data tools work correctly.

Usage:
    python3 test_mcp_server.py
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from schwab_mcp.market_data import (
    get_market_cap,
    get_historical_prices,
    get_company_info,
    MarketDataError,
)


def test_market_cap():
    """Test market cap retrieval."""
    print("📊 Testing get_market_cap(AAPL)...")
    try:
        result = get_market_cap("AAPL")
        print(f"   ✅ Symbol: {result['symbol']}")
        print(f"   ✅ Market Cap: {result['marketCapDisplay']}")
        print(f"   ✅ Exchange: {result['exchange']}")
        return True
    except MarketDataError as e:
        print(f"   ❌ Error: {e}")
        return False


def test_company_info():
    """Test company fundamentals retrieval."""
    print("\n📈 Testing get_company_info(MSFT)...")
    try:
        result = get_company_info("MSFT")
        print(f"   ✅ Symbol: {result['symbol']}")
        print(f"   ✅ Price: ${result['currentPrice']}")
        print(f"   ✅ PE Ratio: {result['trailingPE']:.2f}" if result['trailingPE'] else "   ⚠️  PE Ratio: N/A")
        print(f"   ✅ Market Cap: {result['marketCapDisplay']}")
        return True
    except MarketDataError as e:
        print(f"   ❌ Error: {e}")
        return False


def test_historical_prices():
    """Test historical price retrieval."""
    print("\n📉 Testing get_historical_prices(GOOGL - last 5 days)...")
    try:
        from datetime import datetime, timedelta
        end = datetime.now()
        start = end - timedelta(days=10)

        result = get_historical_prices(
            "GOOGL",
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            "daily"
        )

        if result:
            latest = result[-1]
            print(f"   ✅ Data points: {len(result)}")
            print(f"   ✅ Latest date: {latest['date']}")
            print(f"   ✅ Latest close: ${latest['close']}")
            print(f"   ✅ Volume: {latest['volume']:,}")
            return True
        else:
            print(f"   ⚠️  No data available")
            return False

    except MarketDataError as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Schwab MCP Server Test Suite")
    print("=" * 60)

    results = []

    # Test 1: Market Cap
    results.append(("Market Cap", test_market_cap()))

    # Test 2: Company Info
    results.append(("Company Info", test_company_info()))

    # Test 3: Historical Prices
    results.append(("Historical Prices", test_historical_prices()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! MCP server is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
