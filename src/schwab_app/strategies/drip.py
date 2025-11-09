"""
Dividend Reinvestment (DRIP) strategy
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from schwab_app.client import SchwabClient

logger = logging.getLogger(__name__)


class DRIPStrategy:
    """Dividend Reinvestment Plan strategy implementation"""
    
    def __init__(self, client: SchwabClient, account_number: str):
        """
        Initialize DRIP strategy
        
        Args:
            client: Schwab API client
            account_number: Account number
        """
        self.client = client
        self.account_number = account_number
    
    def execute(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Execute dividend reinvestment strategy
        
        Checks for dividend-paying positions and reinvests available cash
        from recent dividends
        
        Args:
            dry_run: If True, don't actually place orders
            
        Returns:
            List of reinvestment results
        """
        logger.info("Executing DRIP strategy")
        
        try:
            # Get current positions
            positions = self.client.get_positions(self.account_number)
            
            # Get account balances to check cash available
            balances = self.client.get_account_balances(self.account_number)
            cash_available = balances.get("cashAvailableForTrading", 0)
            
            logger.info(f"Cash available for reinvestment: ${cash_available}")
            
            # Filter dividend-paying positions
            dividend_positions = self._get_dividend_positions(positions)
            
            if not dividend_positions:
                logger.info("No dividend-paying positions found")
                return []
            
            # Reinvest in proportion to existing positions
            results = self._reinvest_dividends(
                dividend_positions,
                cash_available,
                dry_run
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to execute DRIP strategy: {e}")
            raise
    
    def _get_dividend_positions(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter positions that pay dividends
        
        Args:
            positions: List of current positions
            
        Returns:
            List of dividend-paying positions
        """
        dividend_positions = []
        
        for position in positions:
            instrument = position.get("instrument", {})
            symbol = instrument.get("symbol", "")
            
            # For simplicity, assume all equity positions may pay dividends
            # In a real implementation, you'd check dividend history
            asset_type = instrument.get("assetType", "")
            if asset_type == "EQUITY":
                dividend_positions.append(position)
        
        return dividend_positions
    
    def _reinvest_dividends(
        self,
        positions: List[Dict[str, Any]],
        cash_available: float,
        dry_run: bool
    ) -> List[Dict[str, Any]]:
        """
        Reinvest cash proportionally to existing positions
        
        Args:
            positions: Dividend-paying positions
            cash_available: Cash available for reinvestment
            dry_run: If True, don't place orders
            
        Returns:
            List of reinvestment results
        """
        if cash_available < 10:  # Minimum threshold
            logger.info(f"Cash available (${cash_available}) below minimum threshold")
            return []
        
        # Calculate total market value
        total_value = sum(
            position.get("marketValue", 0)
            for position in positions
        )
        
        if total_value == 0:
            logger.warning("Total position value is zero")
            return []
        
        results = []
        
        for position in positions:
            instrument = position.get("instrument", {})
            symbol = instrument.get("symbol", "")
            position_value = position.get("marketValue", 0)
            
            # Calculate proportional amount to reinvest
            proportion = position_value / total_value
            reinvest_amount = cash_available * proportion
            
            if reinvest_amount < 5:  # Skip very small amounts
                continue
            
            try:
                result = self._reinvest_in_symbol(symbol, reinvest_amount, dry_run)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to reinvest in {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def _reinvest_in_symbol(self, symbol: str, amount: float, dry_run: bool) -> Dict[str, Any]:
        """
        Reinvest dividends in a specific symbol
        
        Args:
            symbol: Stock symbol
            amount: Amount to reinvest
            dry_run: If True, don't place order
            
        Returns:
            Reinvestment result
        """
        # Get current quote
        quote_data = self.client.get_quote(symbol)
        quote = quote_data.get(symbol, {}).get("quote", {})
        last_price = quote.get("lastPrice", 0)
        
        if last_price == 0:
            raise ValueError(f"Invalid price for {symbol}")
        
        # Calculate shares to buy
        shares = int(amount / last_price)
        
        if shares == 0:
            return {
                "symbol": symbol,
                "status": "skipped",
                "reason": "amount too small",
                "amount": amount,
                "price": last_price
            }
        
        logger.info(f"DRIP: Reinvesting {shares} shares of {symbol} at ~${last_price}")
        
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
