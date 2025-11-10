# API Reference - Schwab Investment App

## Core Classes

### SchwabClient

Main client for interacting with Charles Schwab API.

```python
from schwab_app.client import SchwabClient

client = SchwabClient(
    api_key="your_api_key",
    app_secret="your_app_secret",
    callback_url="https://localhost:8182",
    token_path=".schwab_tokens.json"
)
```

#### Methods

##### `authenticate() -> Client`
Authenticates with Schwab API using OAuth.

##### `get_account_info(account_number: str) -> Dict`
Gets complete account information.

##### `get_account_balances(account_number: str) -> Dict`
Gets account balance information.

##### `get_positions(account_number: str) -> List[Dict]`
Gets current portfolio positions.

##### `get_quote(symbol: str) -> Dict`
Gets real-time quote for a symbol.

##### `get_quotes(symbols: List[str]) -> Dict`
Gets quotes for multiple symbols.

##### `place_order(account_number: str, order: Dict) -> Dict`
Places an order.

##### `get_option_chain(symbol: str, **kwargs) -> Dict`
Gets option chain for a symbol.

---

### DCAStrategy

Dollar Cost Averaging strategy implementation.

```python
from schwab_app.strategies import DCAStrategy

strategy = DCAStrategy(client, account_number)
results = strategy.execute(
    symbols=["SPY", "QQQ"],
    total_amount=100.0,
    dry_run=True
)
```

#### Methods

##### `execute(symbols: List[str], total_amount: float, dry_run: bool = False) -> List[Dict]`
Executes DCA strategy by investing total_amount equally across symbols.

**Parameters:**
- `symbols`: List of stock symbols to invest in
- `total_amount`: Total dollar amount to invest
- `dry_run`: If True, preview only without placing orders

**Returns:** List of order results with status, shares, price, amount

---

### DRIPStrategy

Dividend Reinvestment Plan strategy.

```python
from schwab_app.strategies import DRIPStrategy

strategy = DRIPStrategy(client, account_number)
results = strategy.execute(dry_run=True)
```

#### Methods

##### `execute(dry_run: bool = False) -> List[Dict]`
Reinvests available cash from dividends proportionally to existing positions.

**Returns:** List of reinvestment results

---

### RebalanceStrategy

Portfolio rebalancing strategy.

```python
from schwab_app.strategies import RebalanceStrategy

strategy = RebalanceStrategy(client, account_number)
results = strategy.execute(
    target_allocation={"SPY": 0.60, "AGG": 0.40},
    threshold=0.05,
    dry_run=True
)
```

#### Methods

##### `execute(target_allocation: Dict[str, float], threshold: float = 0.05, dry_run: bool = False) -> List[Dict]`
Rebalances portfolio to match target allocation.

**Parameters:**
- `target_allocation`: Dictionary mapping symbols to target percentages (must sum to 1.0)
- `threshold`: Deviation threshold to trigger rebalancing (e.g., 0.05 = 5%)
- `dry_run`: If True, preview only

**Returns:** List of rebalancing trades

---

### OpportunisticStrategy

Buy-on-dip opportunistic strategy.

```python
from schwab_app.strategies import OpportunisticStrategy

strategy = OpportunisticStrategy(client, account_number)
results = strategy.execute(
    watchlist=["AAPL", "MSFT"],
    dip_threshold=0.03,
    buy_amount=100.0,
    dry_run=True
)
```

#### Methods

##### `execute(watchlist: List[str], dip_threshold: float = 0.03, buy_amount: float = 100.0, dry_run: bool = False) -> List[Dict]`
Monitors watchlist and buys when prices dip.

**Parameters:**
- `watchlist`: List of symbols to monitor
- `dip_threshold`: Percentage dip to trigger buy (e.g., 0.03 = 3%)
- `buy_amount`: Dollar amount to invest per dip
- `dry_run`: If True, preview only

**Returns:** List of buy opportunities acted upon

---

### OptionsStrategy

Options trading strategies (covered calls, protective puts).

```python
from schwab_app.strategies import OptionsStrategy

strategy = OptionsStrategy(client, account_number)

# Covered calls
results = strategy.sell_covered_calls(
    positions=["AAPL"],
    days_to_expiry=30,
    otm_percentage=0.05,
    dry_run=True
)

# Protective puts
results = strategy.buy_protective_puts(
    positions=["AAPL"],
    days_to_expiry=30,
    otm_percentage=0.05,
    dry_run=True
)
```

#### Methods

##### `sell_covered_calls(positions: List[str] = None, days_to_expiry: int = 30, otm_percentage: float = 0.05, dry_run: bool = False) -> List[Dict]`
Sells covered call options on owned positions.

**Parameters:**
- `positions`: List of symbols to sell calls on (None = all eligible)
- `days_to_expiry`: Target days to expiration
- `otm_percentage`: How far out of the money (e.g., 0.05 = 5% above current price)
- `dry_run`: If True, preview only

**Returns:** List of covered call results

##### `buy_protective_puts(positions: List[str] = None, days_to_expiry: int = 30, otm_percentage: float = 0.05, dry_run: bool = False) -> List[Dict]`
Buys protective put options on owned positions.

**Parameters:**
- `positions`: List of symbols to protect (None = all)
- `days_to_expiry`: Target days to expiration
- `otm_percentage`: How far out of the money (e.g., 0.05 = 5% below current price)
- `dry_run`: If True, preview only

**Returns:** List of protective put results

---

### Config

Configuration management class.

```python
from schwab_app.config import Config

# Load from .env file
config = Config()

# Load from specific file
config = Config(env_file=".env.production")

# Validate configuration
config.validate()
```

#### Attributes

- `api_key`: Schwab API key
- `app_secret`: Schwab app secret
- `callback_url`: OAuth callback URL
- `token_path`: Path to token storage
- `account_number`: Account number
- `dca_enabled`: Enable DCA strategy
- `dca_amount`: DCA investment amount
- `dca_frequency`: DCA frequency (daily/weekly/monthly)
- `dca_symbols`: DCA target symbols
- `drip_enabled`: Enable DRIP strategy
- `rebalance_enabled`: Enable rebalancing
- `target_allocation`: Target allocation dictionary
- `rebalance_threshold`: Rebalancing threshold
- `opportunistic_enabled`: Enable opportunistic buying
- `opportunistic_dip_threshold`: Dip threshold for buying
- `options_enabled`: Enable options trading
- `log_level`: Logging level
- `log_file`: Log file path

---

## Order Format Examples

### Market Buy Order
```python
order = {
    "orderType": "MARKET",
    "session": "NORMAL",
    "duration": "DAY",
    "orderStrategyType": "SINGLE",
    "orderLegCollection": [
        {
            "instruction": "BUY",
            "quantity": 10,
            "instrument": {
                "symbol": "SPY",
                "assetType": "EQUITY"
            }
        }
    ]
}
```

### Limit Buy Order
```python
order = {
    "orderType": "LIMIT",
    "session": "NORMAL",
    "duration": "DAY",
    "price": 450.00,
    "orderStrategyType": "SINGLE",
    "orderLegCollection": [
        {
            "instruction": "BUY",
            "quantity": 10,
            "instrument": {
                "symbol": "SPY",
                "assetType": "EQUITY"
            }
        }
    ]
}
```

### Sell Covered Call
```python
order = {
    "orderType": "NET_CREDIT",
    "session": "NORMAL",
    "duration": "DAY",
    "price": 2.50,
    "orderStrategyType": "SINGLE",
    "orderLegCollection": [
        {
            "instruction": "SELL_TO_OPEN",
            "quantity": 1,
            "instrument": {
                "symbol": "SPY_012025C470",
                "assetType": "OPTION"
            }
        }
    ]
}
```

---

## Response Format Examples

### DCA Execute Response
```python
[
    {
        "symbol": "SPY",
        "status": "success",
        "shares": 2,
        "price": 450.25,
        "amount": 900.50,
        "order_id": "12345"
    }
]
```

### Rebalance Response
```python
[
    {
        "symbol": "SPY",
        "status": "success",
        "action": "buy",
        "shares": 5,
        "price": 450.25,
        "value": 2251.25,
        "order_id": "12346"
    }
]
```

### Options Response
```python
[
    {
        "symbol": "SPY",
        "status": "success",
        "contracts": 2,
        "option_symbol": "SPY_012025C470",
        "strike": 470.0,
        "expiry": "2025-01-20",
        "premium": 500.00,
        "order_id": "12347"
    }
]
```

---

## Error Handling

All strategy methods may raise:
- `ValueError`: Invalid parameters or data
- `Exception`: API errors, network issues, authentication failures

Always wrap in try-except:

```python
try:
    results = strategy.execute(symbols, amount, dry_run=False)
except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Execution failed: {e}")
```

---

## Logging

Setup logging before using strategies:

```python
from schwab_app.utils import setup_logging

setup_logging(
    log_level="INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_file="schwab_app.log"  # Optional
)
```

---

## Best Practices

1. **Always use dry_run first**
2. **Validate configuration** with `config.validate()`
3. **Handle exceptions** appropriately
4. **Log all actions** for audit trail
5. **Verify orders** in Schwab account after execution
6. **Start with small amounts** for testing
7. **Monitor logs** regularly
8. **Keep credentials secure** (use .env, never commit)

---

## Rate Limits

Schwab API has rate limits:
- 120 requests per minute per application
- Exceeding limits results in 429 errors
- Implement backoff/retry if needed

---

## Market Hours

Orders placed outside market hours:
- Regular: 9:30 AM - 4:00 PM ET
- Extended: 7:00 AM - 8:00 PM ET (if enabled)
- Use `session="EXTENDED"` for extended hours

---

## Support

For API issues:
- Schwab Developer Portal: https://developer.schwab.com/
- API Documentation: Check portal for latest docs
- GitHub Issues: Report app-specific issues
