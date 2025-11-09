#!/usr/bin/env python3
"""
Example script demonstrating the Schwab Investment App usage
This script shows how to use the various strategies programmatically
"""

from schwab_app.config import Config
from schwab_app.client import SchwabClient
from schwab_app.strategies import (
    DCAStrategy,
    DRIPStrategy,
    RebalanceStrategy,
    OpportunisticStrategy,
    OptionsStrategy,
)
from schwab_app.utils import setup_logging


def main():
    """Main example function"""
    # Setup logging
    setup_logging("INFO")
    
    # Load configuration
    config = Config()
    
    # Note: You'll need to set up your .env file with actual credentials
    # For this example, we'll just show the structure
    
    print("=" * 60)
    print("Schwab Investment App - Example Usage")
    print("=" * 60)
    
    # Initialize client
    # In a real scenario, uncomment these lines after setting up .env
    # client = SchwabClient(
    #     config.api_key,
    #     config.app_secret,
    #     config.callback_url,
    #     config.token_path
    # )
    # client.authenticate()
    
    print("\n1. Dollar Cost Averaging (DCA)")
    print("-" * 60)
    print("Invests fixed amounts at regular intervals")
    print("Example: Invest $100 weekly in SPY, VOO, QQQ")
    # strategy = DCAStrategy(client, config.account_number)
    # results = strategy.execute(["SPY", "VOO", "QQQ"], 100.0, dry_run=True)
    
    print("\n2. Dividend Reinvestment (DRIP)")
    print("-" * 60)
    print("Automatically reinvest dividends proportionally")
    # strategy = DRIPStrategy(client, config.account_number)
    # results = strategy.execute(dry_run=True)
    
    print("\n3. Portfolio Rebalancing")
    print("-" * 60)
    print("Maintain target allocation with automatic rebalancing")
    print("Example: 40% SPY, 30% QQQ, 15% IWM, 15% AGG")
    # strategy = RebalanceStrategy(client, config.account_number)
    # target = {"SPY": 0.40, "QQQ": 0.30, "IWM": 0.15, "AGG": 0.15}
    # results = strategy.execute(target, threshold=0.05, dry_run=True)
    
    print("\n4. Opportunistic Buying")
    print("-" * 60)
    print("Buy on dips - when prices drop by specified threshold")
    print("Example: Buy when stock dips 3% from 52-week high")
    # strategy = OpportunisticStrategy(client, config.account_number)
    # results = strategy.execute(
    #     ["AAPL", "MSFT", "GOOGL"],
    #     dip_threshold=0.03,
    #     buy_amount=100.0,
    #     dry_run=True
    # )
    
    print("\n5. Options Trading - Covered Calls")
    print("-" * 60)
    print("Sell covered calls to generate premium income")
    # strategy = OptionsStrategy(client, config.account_number)
    # results = strategy.sell_covered_calls(
    #     positions=["AAPL", "MSFT"],
    #     days_to_expiry=30,
    #     otm_percentage=0.05,
    #     dry_run=True
    # )
    
    print("\n6. Options Trading - Protective Puts")
    print("-" * 60)
    print("Buy protective puts for downside protection")
    # strategy = OptionsStrategy(client, config.account_number)
    # results = strategy.buy_protective_puts(
    #     positions=["AAPL", "MSFT"],
    #     days_to_expiry=30,
    #     otm_percentage=0.05,
    #     dry_run=True
    # )
    
    print("\n" + "=" * 60)
    print("To use this app:")
    print("1. Set up your .env file with Schwab API credentials")
    print("2. Run: schwab-invest balance (to test connection)")
    print("3. Use --dry-run flag to preview actions before executing")
    print("4. Run specific strategies as needed")
    print("=" * 60)


if __name__ == "__main__":
    main()
