# Schwab Investment App

A comprehensive Python application for automated investment strategies using the Charles Schwab API. This application provides tools for account management, dollar cost averaging (DCA), dividend reinvestment (DRIP), portfolio rebalancing, opportunistic buying on market dips, and options trading strategies.

## Features

### Core Functionality
- **Account Balance Checking**: Monitor your account balances and positions in real-time
- **Dollar Cost Averaging (DCA)**: Automatically invest fixed amounts at regular intervals
- **Dividend Reinvestment (DRIP)**: Automatically reinvest dividends proportionally
- **Portfolio Rebalancing**: Maintain target asset allocation with automatic rebalancing
- **Opportunistic Buying**: Buy stocks when they dip below specified thresholds
- **Options Trading**: 
  - Sell covered calls to generate income
  - Buy protective puts for downside protection

### Technical Features
- Rich CLI interface with colored output and tables
- Dry-run mode for all strategies to preview actions without executing
- Comprehensive logging (console and JSON file logging)
- Configuration via environment variables or .env file
- Robust error handling and validation

## Installation

### Prerequisites
- Python 3.8 or higher
- Charles Schwab API credentials (API key and app secret)
- A Charles Schwab brokerage account

### Setup

1. Clone the repository:
```bash
git clone https://github.com/hdylizardeIdP/verbose-palm-tree.git
cd verbose-palm-tree
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package:
```bash
pip install -e .
```

4. Configure your credentials:
```bash
cp .env.example .env
# Edit .env and add your Schwab API credentials
```

## Configuration

### Getting Schwab API Credentials

1. Visit the [Charles Schwab Developer Portal](https://developer.schwab.com/)
2. Create an app to get your API key and app secret
3. Set up OAuth callback URL (default: https://localhost:8182)

### Environment Variables

Edit the `.env` file with your configuration:

```bash
# Schwab API Credentials
SCHWAB_API_KEY=your_api_key_here
SCHWAB_APP_SECRET=your_app_secret_here
SCHWAB_CALLBACK_URL=https://localhost:8182
SCHWAB_TOKEN_PATH=.schwab_tokens.json

# Account Configuration
SCHWAB_ACCOUNT_NUMBER=your_account_hash_here

# Strategy Configuration
DCA_ENABLED=false
DCA_AMOUNT=100.0
DCA_SYMBOLS=SPY,VOO,QQQ

DRIP_ENABLED=false

REBALANCE_ENABLED=false
REBALANCE_THRESHOLD=0.05
TARGET_ALLOCATION={"SPY": 0.40, "QQQ": 0.30, "IWM": 0.15, "AGG": 0.15}

OPPORTUNISTIC_ENABLED=false
OPPORTUNISTIC_DIP_THRESHOLD=0.03

OPTIONS_ENABLED=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=schwab_app.log
```

## Usage

### First-Time Authentication

On first run, you'll need to complete OAuth authentication:

```bash
schwab-invest balance
```

This will open a browser for you to authorize the app. After authorization, tokens will be saved to `.schwab_tokens.json` for future use.

### Check Account Balance

```bash
schwab-invest balance
```

### View Current Positions

```bash
schwab-invest positions
```

### Dollar Cost Averaging

Execute DCA strategy:
```bash
# Use configuration from .env
schwab-invest dca

# Override with custom values
schwab-invest dca --amount 200 --symbols "SPY,QQQ,VTI"

# Dry run to preview actions
schwab-invest dca --dry-run
```

### Dividend Reinvestment

Reinvest available cash from dividends:
```bash
schwab-invest drip

# Dry run
schwab-invest drip --dry-run
```

### Portfolio Rebalancing

Rebalance portfolio to target allocation:
```bash
# Use configuration from .env
schwab-invest rebalance

# Custom threshold
schwab-invest rebalance --threshold 0.10

# Dry run
schwab-invest rebalance --dry-run
```

### Opportunistic Buying

Buy stocks on dips:
```bash
# Use configuration from .env
schwab-invest opportunistic

# Custom parameters
schwab-invest opportunistic --symbols "AAPL,MSFT,GOOGL" --threshold 0.05 --amount 150

# Dry run
schwab-invest opportunistic --dry-run
```

### Options Strategies

Sell covered calls:
```bash
# Sell covered calls on all eligible positions
schwab-invest covered-calls

# Specific symbols only
schwab-invest covered-calls --symbols "AAPL,MSFT"

# Dry run
schwab-invest covered-calls --dry-run
```

Buy protective puts:
```bash
# Buy protective puts on all positions
schwab-invest protective-puts

# Specific symbols only
schwab-invest protective-puts --symbols "AAPL,MSFT"

# Dry run
schwab-invest protective-puts --dry-run
```

### Global Options

All commands support:
- `--env-file PATH`: Use a specific .env file
- `--log-level LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)

Example:
```bash
schwab-invest --env-file .env.production --log-level DEBUG balance
```

## Strategies Explained

### Dollar Cost Averaging (DCA)
Invests a fixed dollar amount in specified securities at regular intervals, regardless of price. This reduces the impact of volatility by averaging the purchase price over time.

### Dividend Reinvestment (DRIP)
Automatically uses cash from dividends to purchase additional shares of dividend-paying positions, proportional to their current allocation.

### Portfolio Rebalancing
Maintains target asset allocation by buying underweight positions and selling overweight positions when they deviate beyond the specified threshold.

### Opportunistic Buying
Monitors a watchlist for price dips (either from 52-week highs or intraday drops) and automatically purchases when the dip threshold is met.

### Covered Calls
Sells call options on stocks you own to generate premium income. If the stock price rises above the strike price, shares may be called away.

### Protective Puts
Buys put options to protect against downside risk. Acts as insurance for your positions.

## Safety Features

- **Dry Run Mode**: All strategies support `--dry-run` to preview actions without executing trades
- **Configuration Validation**: Validates API credentials and configuration before executing
- **Comprehensive Logging**: All actions are logged with timestamps and details
- **Error Handling**: Graceful error handling with informative messages
- **Market Hours**: Respects market hours for order placement

## Project Structure

```
verbose-palm-tree/
├── src/
│   └── schwab_app/
│       ├── __init__.py
│       ├── cli.py              # Command-line interface
│       ├── client.py           # Schwab API client wrapper
│       ├── config.py           # Configuration management
│       ├── strategies/
│       │   ├── __init__.py
│       │   ├── dca.py          # Dollar cost averaging
│       │   ├── drip.py         # Dividend reinvestment
│       │   ├── rebalance.py    # Portfolio rebalancing
│       │   ├── opportunistic.py # Opportunistic buying
│       │   └── options.py      # Options trading
│       └── utils/
│           ├── __init__.py
│           └── logging_config.py
├── requirements.txt
├── setup.py
├── .env.example
├── .gitignore
└── README.md
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
The project follows PEP 8 guidelines. Use linters:
```bash
# Install dev dependencies
pip install black flake8 mypy

# Format code
black src/

# Lint
flake8 src/

# Type checking
mypy src/
```

## Security Considerations

- **Never commit your .env file** - it contains sensitive API credentials
- **Tokens are stored locally** in `.schwab_tokens.json` - keep this file secure
- **Use paper trading account** for testing before using real money
- **Review all dry-run outputs** before executing real trades
- **Set appropriate position limits** to manage risk
- **Monitor your account regularly** for unexpected activity

## Disclaimer

**This software is for educational and informational purposes only. It is not financial advice.**

- Trading stocks and options carries significant risk
- Past performance does not guarantee future results
- You are solely responsible for your investment decisions
- The authors are not responsible for any financial losses
- Always do your own research and consult a financial advisor
- Test thoroughly with a paper trading account before using real money

## License

This project is provided as-is for educational purposes.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues, questions, or contributions, please open an issue on GitHub.

## Acknowledgments

- Built using the [schwab-py](https://github.com/itsjafer/schwab-py) library
- Charles Schwab API documentation: https://developer.schwab.com/
- Rich library for beautiful terminal output
