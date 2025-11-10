"""
Opportunistic buying strategy - buy on dips
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from schwab_app.client import SchwabClient

logger = logging.getLogger(__name__)


class OpportunisticStrategy:
    """Opportunistic buying strategy - buy when prices dip"""
    
    def __init__(self, client: SchwabClient, account_number: str):
        """
        Initialize opportunistic strategy
        
        Args:
            client: Schwab API client
            account_number: Account number
        """
        self.client = client
        self.account_number = account_number
    
    def execute(
        self,
        watchlist: List[str],
        dip_threshold: float = 0.03,
        buy_amount: float = 100.0,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute opportunistic buying on price dips
        
        Args:
            watchlist: List of symbols to watch
            dip_threshold: Percentage dip to trigger buy (e.g., 0.03 for 3%)
            buy_amount: Amount to invest per dip
            dry_run: If True, don't place orders
            
        Returns:
            List of buy opportunities and results
        """
        logger.info(f"Executing opportunistic strategy for {len(watchlist)} symbols")
        logger.info(f"Looking for {dip_threshold*100}% dips with ${buy_amount} per buy")
        
        results = []
        
        for symbol in watchlist:
            try:
                result = self._check_symbol_for_dip(
                    symbol,
                    dip_threshold,
                    buy_amount,
                    dry_run
                )
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Failed to check {symbol}: {e}")
        
        return results
    
    def _check_symbol_for_dip(
        self,
        symbol: str,
        dip_threshold: float,
        buy_amount: float,
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Check if a symbol has dipped enough to buy
        
        Args:
            symbol: Stock symbol
            dip_threshold: Dip percentage threshold
            buy_amount: Amount to buy
            dry_run: If True, don't place order
            
        Returns:
            Result dictionary if dip detected, None otherwise
        """
        # Get current quote
        quote_data = self.client.get_quote(symbol)
        quote = quote_data.get(symbol, {}).get("quote", {})
        
        last_price = quote.get("lastPrice", 0)
        open_price = quote.get("openPrice", 0)
        high_52_week = quote.get("52WkHigh", 0)
        
        if last_price == 0 or high_52_week == 0:
            logger.warning(f"Invalid price data for {symbol}")
            return None
        
        # Calculate dip from 52-week high
        dip_from_high = (high_52_week - last_price) / high_52_week
        
        # Calculate intraday change
        intraday_change = 0
        if open_price > 0:
            intraday_change = (last_price - open_price) / open_price
        
        logger.debug(
            f"{symbol}: Price ${last_price}, 52w High ${high_52_week}, "
            f"Dip from high: {dip_from_high:.2%}, Intraday: {intraday_change:.2%}"
        )
        
        # Check if we have a buying opportunity
        # Either significant dip from 52-week high OR sharp intraday drop
        is_dip = (
            dip_from_high >= dip_threshold or
            (intraday_change < 0 and abs(intraday_change) >= dip_threshold)
        )
        
        if not is_dip:
            return None
        
        logger.info(
            f"Opportunity detected for {symbol}: "
            f"Dip from 52w high: {dip_from_high:.2%}, Intraday: {intraday_change:.2%}"
        )
        
        # Execute buy
        return self._execute_opportunistic_buy(
            symbol,
            last_price,
            buy_amount,
            dip_from_high,
            dry_run
        )
    
    def _execute_opportunistic_buy(
        self,
        symbol: str,
        price: float,
        amount: float,
        dip_percentage: float,
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Execute an opportunistic buy order
        
        Args:
            symbol: Stock symbol
            price: Current price
            amount: Amount to invest
            dip_percentage: Percentage dip detected
            dry_run: If True, don't place order
            
        Returns:
            Buy result
        """
        # Calculate shares
        shares = int(amount / price)
        
        if shares == 0:
            return {
                "symbol": symbol,
                "status": "skipped",
                "reason": "amount too small",
                "amount": amount,
                "price": price,
                "dip": dip_percentage
            }
        
        logger.info(
            f"Opportunistic buy: {shares} shares of {symbol} at ~${price} "
            f"(dip: {dip_percentage:.2%})"
        )
        
        if dry_run:
            return {
                "symbol": symbol,
                "status": "dry_run",
                "shares": shares,
                "price": price,
                "amount": shares * price,
                "dip": dip_percentage
            }
        
        # Create market buy order
        order = {
            "orderType": "MARKET",
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": "BUY",
                    "quantity": shares,
                    "instrument": {
                        "symbol": symbol,
                        "assetType": "EQUITY"
                    }
                }
            ]
        }
        
        # Place order
        order_result = self.client.place_order(self.account_number, order)
        
        return {
            "symbol": symbol,
            "status": "success",
            "shares": shares,
            "price": price,
            "amount": shares * price,
            "dip": dip_percentage,
            "order_id": order_result.get("order_id")
        }
