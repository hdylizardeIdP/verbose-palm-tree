"""
Dollar Cost Averaging (DCA) strategy
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
from schwab_app.client import SchwabClient

logger = logging.getLogger(__name__)


class DCAStrategy:
    """Dollar Cost Averaging strategy implementation"""
    
    def __init__(self, client: SchwabClient, account_number: str):
        """
        Initialize DCA strategy
        
        Args:
            client: Schwab API client
            account_number: Account number
        """
        self.client = client
        self.account_number = account_number
    
    def execute(self, symbols: List[str], total_amount: float, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Execute dollar cost averaging strategy
        
        Args:
            symbols: List of symbols to invest in
            total_amount: Total amount to invest
            dry_run: If True, don't actually place orders
            
        Returns:
            List of order results
        """
        logger.info(f"Executing DCA strategy: ${total_amount} across {symbols}")
        
        if not symbols:
            logger.warning("No symbols provided for DCA")
            return []
        
        # Divide amount equally among symbols
        amount_per_symbol = total_amount / len(symbols)
        
        results = []
        for symbol in symbols:
            try:
                result = self._invest_in_symbol(symbol, amount_per_symbol, dry_run)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to invest in {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def _invest_in_symbol(self, symbol: str, amount: float, dry_run: bool) -> Dict[str, Any]:
        """
        Invest a specific amount in a symbol
        
        Args:
            symbol: Stock symbol
            amount: Amount to invest
            dry_run: If True, don't actually place order
            
        Returns:
            Order result
        """
        # Get current quote
        quote_data = self.client.get_quote(symbol)
        quote = quote_data.get(symbol, {}).get("quote", {})
        last_price = quote.get("lastPrice", 0)
        
        if last_price == 0:
            raise ValueError(f"Invalid price for {symbol}")
        
        # Calculate number of shares
        shares = int(amount / last_price)
        
        if shares == 0:
            logger.warning(f"Amount ${amount} too small to buy {symbol} at ${last_price}")
            return {
                "symbol": symbol,
                "status": "skipped",
                "reason": "amount too small",
                "amount": amount,
                "price": last_price
            }
        
        logger.info(f"DCA: Buying {shares} shares of {symbol} at ~${last_price} (total: ~${shares * last_price})")
        
        if dry_run:
            return {
                "symbol": symbol,
                "status": "dry_run",
                "shares": shares,
                "price": last_price,
                "amount": shares * last_price
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
            "price": last_price,
            "amount": shares * last_price,
            "order_id": order_result.get("order_id")
        }
