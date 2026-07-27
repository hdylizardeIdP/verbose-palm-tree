# Schwab MCP Server Setup Guide

This guide explains how to configure and use the Schwab MCP server for both **Claude Code (CLI)** and **Claude Desktop**.

## Overview

The Schwab MCP server provides real-time market data including:
- **Live prices** (bid, ask, last, volume)
- **Market cap** and company information
- **Historical price data** (daily, weekly, monthly)
- **Company fundamentals** (PE ratio, EPS, dividends, ROE, etc.)

## Installation

### 1. Install Dependencies

```bash
cd /Users/david/verbose-palm-tree
pip install -r requirements.txt
```

This installs:
- `yfinance==0.2.33` - Market data provider
- `mcp==1.9.0` - Model Context Protocol SDK

## Claude Code (CLI) Setup

### Quick Start

The project-level configuration is ready to use. When you run Claude Code in this directory, it will automatically load the Schwab MCP server from the `.claude/settings.json` file.

```bash
cd /Users/david/verbose-palm-tree
claude
```

The server is configured with:
- Command: `python3 -m schwab_mcp.server`
- Working directory: `/Users/david/verbose-palm-tree/src`

### Manual Setup (Global)

If you want to make the Schwab server available globally across all projects, create `~/.claude/.mcp.json`:

```json
{
  "mcpServers": {
    "schwab": {
      "command": "python3",
      "args": ["-m", "schwab_mcp.server"],
      "cwd": "/Users/david/verbose-palm-tree/src"
    }
  }
}
```

Then approve it when Claude Code prompts:
```
MCP Server: schwab
Command: python3 -m schwab_mcp.server
Approve? (y/n)
```

## Claude Desktop Setup

### 1. Locate Claude Desktop Config

Claude Desktop stores its MCP configuration in:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### 2. Update Configuration

Add the Schwab server to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "schwab": {
      "command": "python3",
      "args": ["-m", "schwab_mcp.server"],
      "cwd": "/Users/david/verbose-palm-tree/src",
      "env": {}
    }
  }
}
```

**Example full config:**
```json
{
  "mcpServers": {
    "schwab": {
      "command": "python3",
      "args": ["-m", "schwab_mcp.server"],
      "cwd": "/Users/david/verbose-palm-tree/src",
      "env": {}
    }
  }
}
```

### 3. Restart Claude Desktop

Quit and reopen Claude Desktop to load the new MCP server configuration.

## Testing the Server

### Test in Claude Code

```bash
cd /Users/david/verbose-palm-tree
claude
```

Then ask Claude:
> Get market cap info for AAPL

Expected response:
```
Symbol: AAPL
Market Cap: $4.94T
Currency: USD
Exchange: NASDAQ
Sector: Technology
```

### Test in Claude Desktop

1. Open Claude Desktop
2. Click the "Tools" button or press the MCP icon
3. Verify "schwab" appears in the MCP servers list
4. Ask Claude:
   > What's the market cap of MSFT?

## Available Tools

### `get_market_cap_info(symbol: str)`
Get market cap and basic company information.

**Example:**
```
{
  "symbol": "AAPL",
  "marketCap": 4940000000000,
  "marketCapDisplay": "$4.94T",
  "currency": "USD",
  "exchange": "NASDAQ",
  "longName": "Apple Inc.",
  "industry": "Consumer Electronics",
  "sector": "Technology"
}
```

### `get_historical_price_data(symbol, start_date, end_date, interval)`
Get historical OHLCV data.

**Parameters:**
- `symbol`: Stock ticker (e.g., "AAPL")
- `start_date`: Start date in "YYYY-MM-DD" format (default: 1 year ago)
- `end_date`: End date in "YYYY-MM-DD" format (default: today)
- `interval`: "daily", "weekly", or "monthly" (default: "daily")

**Example:**
```
{
  "symbol": "GOOGL",
  "interval": "daily",
  "prices": [
    {
      "date": "2025-07-24",
      "open": 318.50,
      "high": 320.75,
      "low": 317.25,
      "close": 319.74,
      "volume": 31740600
    },
    ...
  ]
}
```

### `get_company_fundamentals(symbol: str)`
Get detailed company metrics.

**Example:**
```
{
  "symbol": "MSFT",
  "currentPrice": 391.94,
  "trailingPE": 23.34,
  "trailingEPS": 16.81,
  "dividendYield": 0.0072,
  "beta": 0.95,
  "fiftyTwoWeekHigh": 432.85,
  "fiftyTwoWeekLow": 327.15,
  "roe": 0.2456,
  "roa": 0.1234,
  "debtToEquity": 0.45
}
```

## Troubleshooting

### MCP Server Not Found

**Claude Code:**
1. Verify the project `.claude/settings.json` exists
2. Check the file permissions: `ls -la .claude/settings.json`
3. Try running: `python3 -m schwab_mcp.server` directly to test

**Claude Desktop:**
1. Check the config file: `cat ~/Library/Application\ Support/Claude/claude_desktop_config.json`
2. Verify the path `/Users/david/verbose-palm-tree/src` exists
3. Restart Claude Desktop completely (⌘Q and reopen)

### Connection Refused

```
Error: Failed to fetch market cap for AAPL
```

This usually means:
1. Dependencies not installed: Run `pip install -r requirements.txt`
2. Wrong Python path: Verify `python3 -m schwab_mcp.server` works from the src directory
3. Network issue: yfinance requires internet connection

### No Data Available

```
Error: Market cap data not available for INVALID
```

This means the ticker symbol is invalid or yfinance doesn't have data for it. Try:
- Verify the ticker on Yahoo Finance: `https://finance.yahoo.com/quote/SYMBOL`
- Common symbols: AAPL, MSFT, GOOGL, TSLA, META, AMZN

## Performance Notes

- **Caching**: Market data is cached for 5 minutes to reduce API calls
- **Rate Limits**: yfinance doesn't have strict rate limits for market data
- **Historical Data**: Requesting 10+ years of daily data may take 2-3 seconds

## What's Next

### Phase 2 (Future)
- Add Polygon.io as premium alternative with redundancy
- Implement database caching for historical data
- Add price alert capabilities
- Support for crypto and other asset classes

### Integration with Schwab Portfolio
Combine with existing `get_positions()` tool to analyze:
- Position valuations vs market cap
- P/E ratios of held securities
- Sector allocation vs market
- Historical performance analysis

## Files Modified

```
requirements.txt                     # Added yfinance and mcp
.claude/settings.json               # Created - project MCP config
src/schwab_mcp/market_data.py       # Created - yfinance wrapper
src/schwab_mcp/server.py            # Updated - added 3 new tools
```

## Detailed Configuration

### Project-Level Config (`.claude/settings.json`)
```json
{
  "mcpServers": {
    "schwab": {
      "command": "python3",
      "args": ["-m", "schwab_mcp.server"],
      "cwd": "/Users/david/verbose-palm-tree/src",
      "env": {}
    }
  },
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read",
      "Edit",
      "Write",
      "mcp__schwab__*"
    ]
  }
}
```

**Key fields:**
- `command`: Python 3 executable
- `args`: Module path to run the server
- `cwd`: Working directory (must have schwab_mcp module)
- `env`: Additional environment variables (empty by default)

### Desktop Config Path
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

Same MCP server config structure as above.

## Questions?

Test the server directly:
```bash
cd /Users/david/verbose-palm-tree/src
python3 -m schwab_mcp.server
```

This starts the MCP server in stdio mode. You'll see:
```
INFO: Starting MCP server "schwab"...
INFO: Server ready
```

Press Ctrl+C to stop.
