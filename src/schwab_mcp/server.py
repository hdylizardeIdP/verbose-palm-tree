"""
Schwab MCP Server - Read-only portfolio data tools.

Usage:
    python -m schwab_mcp.server

Register in Claude's MCP config:
    {
      "mcpServers": {
        "schwab": {
          "command": "python",
          "args": ["-m", "schwab_mcp.server"],
          "cwd": "/path/to/verbose-palm-tree/src"
        }
      }
    }
"""

import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Add parent to path for schwab_app imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schwab_app.client import SchwabClient
from schwab_app.config import Config

mcp = FastMCP("schwab")

_client: Optional[SchwabClient] = None
_config: Optional[Config] = None


def get_client() -> SchwabClient:
    """Get or initialize the Schwab client."""
    global _client, _config
    if _client is None:
        _config = Config()
        _config.validate(require_account=True)
        _client = SchwabClient(
            _config.api_key,
            _config.app_secret,
            _config.callback_url,
            _config.token_path,
        )
    return _client


def get_account() -> str:
    """Get the configured account number."""
    global _config
    if _config is None:
        _config = Config()
        _config.validate(require_account=True)
    return _config.account_number


@mcp.tool()
def get_balances() -> dict:
    """
    Get account balances including cash, buying power, and portfolio value.

    Returns:
        Dictionary with liquidationValue, cashAvailableForTrading,
        buyingPower, and marketValue.
    """
    client = get_client()
    account = get_account()
    balances = client.get_account_balances(account)
    return {
        "liquidationValue": balances.get("liquidationValue", 0),
        "cashAvailableForTrading": balances.get("cashAvailableForTrading", 0),
        "buyingPower": balances.get("buyingPower", 0),
        "marketValue": balances.get("marketValue", 0),
    }


@mcp.tool()
def get_positions() -> list[dict]:
    """
    Get all current positions with P/L calculations.

    Returns:
        List of positions, each with symbol, assetType, quantity, avgPrice,
        marketValue, costBasis, pnl, and pnlPercent.
    """
    client = get_client()
    account = get_account()
    raw_positions = client.get_positions(account)

    positions = []
    for pos in raw_positions:
        instrument = pos.get("instrument", {})
        symbol = instrument.get("symbol", "")
        asset_type = instrument.get("assetType", "EQUITY")
        quantity = pos.get("longQuantity", 0)
        avg_price = pos.get("averagePrice", 0)
        market_value = pos.get("marketValue", 0)
        cost_basis = quantity * avg_price
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

        positions.append({
            "symbol": symbol,
            "assetType": asset_type,
            "quantity": quantity,
            "avgPrice": round(avg_price, 2),
            "marketValue": round(market_value, 2),
            "costBasis": round(cost_basis, 2),
            "pnl": round(pnl, 2),
            "pnlPercent": round(pnl_pct, 2),
        })

    return positions


@mcp.tool()
def get_quotes(symbols: list[str]) -> dict:
    """
    Get current quotes for one or more symbols.

    Args:
        symbols: List of stock symbols (e.g., ["AAPL", "MSFT"])

    Returns:
        Dictionary mapping each symbol to its quote data including
        lastPrice, bidPrice, askPrice, totalVolume, and netChange.
    """
    if not symbols:
        return {}

    client = get_client()
    raw_quotes = client.get_quotes(symbols)

    quotes = {}
    for symbol, data in raw_quotes.items():
        quote = data.get("quote", {})
        quotes[symbol] = {
            "lastPrice": quote.get("lastPrice", 0),
            "bidPrice": quote.get("bidPrice", 0),
            "askPrice": quote.get("askPrice", 0),
            "totalVolume": quote.get("totalVolume", 0),
            "netChange": quote.get("netChange", 0),
            "netPercentChange": quote.get("netPercentChangeInDouble", 0),
            "high": quote.get("highPrice", 0),
            "low": quote.get("lowPrice", 0),
            "open": quote.get("openPrice", 0),
            "close": quote.get("closePrice", 0),
        }

    return quotes


@mcp.tool()
def get_orders(status: Optional[str] = None) -> list[dict]:
    """
    Get recent orders for the account.

    Args:
        status: Optional filter by order status (e.g., "FILLED", "PENDING",
                "CANCELED"). If not provided, returns all recent orders.

    Returns:
        List of orders with orderId, symbol, instruction (BUY/SELL),
        quantity, price, status, and enteredTime.
    """
    client = get_client()
    account = get_account()

    kwargs = {}
    if status:
        kwargs["status"] = status

    raw_orders = client.get_orders(account, **kwargs)

    orders = []
    for order in raw_orders:
        order_legs = order.get("orderLegCollection", [])
        if not order_legs:
            continue

        leg = order_legs[0]
        instrument = leg.get("instrument", {})

        orders.append({
            "orderId": order.get("orderId"),
            "symbol": instrument.get("symbol", ""),
            "instruction": leg.get("instruction", ""),
            "quantity": leg.get("quantity", 0),
            "price": order.get("price", 0),
            "status": order.get("status", ""),
            "enteredTime": order.get("enteredTime", ""),
            "filledQuantity": order.get("filledQuantity", 0),
            "orderType": order.get("orderType", ""),
        })

    return orders


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
