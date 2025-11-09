# Schwab Investment App - Quick Reference

## Installation
```bash
pip install -r requirements.txt
pip install -e .
```

## Initial Setup
```bash
cp .env.example .env
# Edit .env with your credentials
schwab-invest balance  # First auth
```

## Commands Quick Reference

### Account Information
```bash
schwab-invest balance                    # Check account balances
schwab-invest positions                  # View current positions
```

### Dollar Cost Averaging
```bash
schwab-invest dca                        # Use config defaults
schwab-invest dca --amount 100           # Invest $100
schwab-invest dca --symbols "SPY,QQQ"    # Specific symbols
schwab-invest dca --dry-run              # Preview only
```

### Dividend Reinvestment
```bash
schwab-invest drip                       # Reinvest dividends
schwab-invest drip --dry-run             # Preview only
```

### Portfolio Rebalancing
```bash
schwab-invest rebalance                  # Use config defaults
schwab-invest rebalance --threshold 0.10 # 10% threshold
schwab-invest rebalance --dry-run        # Preview only
```

### Opportunistic Buying
```bash
schwab-invest opportunistic                                    # Use config defaults
schwab-invest opportunistic --symbols "AAPL,MSFT,GOOGL"       # Specific watchlist
schwab-invest opportunistic --threshold 0.05 --amount 100     # Custom parameters
schwab-invest opportunistic --dry-run                         # Preview only
```

### Options Trading
```bash
# Covered Calls
schwab-invest covered-calls                      # All eligible positions
schwab-invest covered-calls --symbols "AAPL"     # Specific symbols
schwab-invest covered-calls --dry-run            # Preview only

# Protective Puts
schwab-invest protective-puts                    # All positions
schwab-invest protective-puts --symbols "AAPL"   # Specific symbols
schwab-invest protective-puts --dry-run          # Preview only
```

## Configuration (.env)

### Required
```bash
SCHWAB_API_KEY=your_api_key
SCHWAB_APP_SECRET=your_app_secret
SCHWAB_ACCOUNT_NUMBER=your_account_hash
```

### Optional Strategy Settings
```bash
# DCA
DCA_ENABLED=true
DCA_AMOUNT=100.0
DCA_FREQUENCY=weekly          # daily, weekly, monthly
DCA_SYMBOLS=SPY,VOO,QQQ

# Rebalancing
REBALANCE_ENABLED=true
REBALANCE_THRESHOLD=0.05      # 5%
TARGET_ALLOCATION={"SPY": 0.40, "QQQ": 0.30, "IWM": 0.15, "AGG": 0.15}

# Opportunistic
OPPORTUNISTIC_ENABLED=true
OPPORTUNISTIC_DIP_THRESHOLD=0.03  # 3%
```

## Global Options
```bash
--env-file PATH      # Use specific .env file
--log-level LEVEL    # DEBUG, INFO, WARNING, ERROR
```

## Examples

### Basic Workflow
```bash
# 1. Check current state
schwab-invest balance
schwab-invest positions

# 2. Preview a strategy
schwab-invest dca --amount 50 --dry-run

# 3. Execute if preview looks good
schwab-invest dca --amount 50

# 4. Check results
schwab-invest positions
tail -20 schwab_app.log
```

### Weekly DCA Routine
```bash
# Every Monday morning
schwab-invest dca --amount 200 --symbols "SPY,QQQ,VTI"
```

### Monthly Rebalancing
```bash
# First Friday of the month
schwab-invest rebalance --threshold 0.05
```

### Check for Opportunities
```bash
# Several times per day
schwab-invest opportunistic --symbols "AAPL,MSFT,GOOGL,NVDA" --threshold 0.03
```

## Automated Scheduling
```bash
# Run scheduler as background service
python examples/scheduler.py &

# Or use cron (Linux/Mac)
crontab -e
# Add: 30 9 * * 1 cd /path/to/app && schwab-invest dca
```

## Monitoring
```bash
# Watch logs
tail -f schwab_app.log

# Check recent activity
schwab-invest positions
grep "Order placed" schwab_app.log | tail -10
```

## Safety Tips
- ✅ Always use `--dry-run` first
- ✅ Start with small amounts
- ✅ Review logs regularly
- ✅ Verify orders in Schwab account
- ✅ Keep `.env` and tokens secure
- ❌ Never commit credentials
- ❌ Don't run untested on production
- ❌ Don't exceed risk tolerance

## Troubleshooting
```bash
# Auth issues
rm .schwab_tokens.json
schwab-invest balance

# Debug mode
schwab-invest --log-level DEBUG balance

# Check logs
tail -100 schwab_app.log | grep ERROR
```

## Strategy Defaults

| Strategy | Default Behavior |
|----------|------------------|
| DCA | Equal distribution across symbols |
| DRIP | Proportional to position size |
| Rebalance | 5% deviation threshold |
| Opportunistic | 3% dip from 52-week high |
| Covered Calls | 30 DTE, 5% OTM |
| Protective Puts | 30 DTE, 5% OTM |

## File Locations
```
.env                    # Your configuration
.schwab_tokens.json     # OAuth tokens (auto-generated)
schwab_app.log          # Application logs
examples/               # Example scripts
```

## Resources
- Schwab API Docs: https://developer.schwab.com/
- GitHub Issues: https://github.com/hdylizardeIdP/verbose-palm-tree/issues
- Testing Guide: TESTING.md
- Full README: README.md
