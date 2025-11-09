"""
Portfolio Rebalancing strategy
"""
import logging
from typing import Dict, Any, List
from schwab_app.client import SchwabClient

logger = logging.getLogger(__name__)


class RebalanceStrategy:
    """Portfolio rebalancing strategy implementation"""
    
    def __init__(self, client: SchwabClient, account_number: str):
        """
        Initialize rebalancing strategy
        
        Args:
            client: Schwab API client
            account_number: Account number
        """
        self.client = client
        self.account_number = account_number
    
    def execute(
        self,
        target_allocation: Dict[str, float],
        threshold: float = 0.05,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute portfolio rebalancing
        
        Args:
            target_allocation: Target allocation percentages (symbol: percentage)
            threshold: Rebalancing threshold (e.g., 0.05 for 5%)
            dry_run: If True, don't actually place orders
            
        Returns:
            List of rebalancing actions
        """
        logger.info(f"Executing rebalancing strategy with {threshold*100}% threshold")
        
        try:
            # Get current positions
            positions = self.client.get_positions(self.account_number)
            balances = self.client.get_account_balances(self.account_number)
            
            # Calculate current allocation
            current_allocation = self._calculate_current_allocation(positions, balances)
            
            # Determine rebalancing actions
            actions = self._calculate_rebalancing_actions(
                current_allocation,
                target_allocation,
                threshold
            )
            
            if not actions:
                logger.info("Portfolio is balanced, no actions needed")
                return []
            
            # Execute rebalancing trades
            results = self._execute_rebalancing(actions, dry_run)
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to execute rebalancing strategy: {e}")
            raise
    
    def _calculate_current_allocation(
        self,
        positions: List[Dict[str, Any]],
        balances: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate current portfolio allocation
        
        Args:
            positions: Current positions
            balances: Account balances
            
        Returns:
            Dictionary of symbol: percentage allocation
        """
        total_value = balances.get("liquidationValue", 0)
        
        if total_value == 0:
            logger.warning("Total portfolio value is zero")
            return {}
        
        allocation = {}
        
        for position in positions:
            instrument = position.get("instrument", {})
            symbol = instrument.get("symbol", "")
            market_value = position.get("marketValue", 0)
            
            if symbol and market_value > 0:
                allocation[symbol] = market_value / total_value
        
        return allocation
    
    def _calculate_rebalancing_actions(
        self,
        current: Dict[str, float],
        target: Dict[str, float],
        threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Calculate what trades are needed to rebalance
        
        Args:
            current: Current allocation percentages
            target: Target allocation percentages
            threshold: Deviation threshold to trigger rebalancing
            
        Returns:
            List of rebalancing actions
        """
        actions = []
        
        # Check each target symbol
        for symbol, target_pct in target.items():
            current_pct = current.get(symbol, 0)
            deviation = abs(current_pct - target_pct)
            
            if deviation > threshold:
                action = {
                    "symbol": symbol,
                    "current_allocation": current_pct,
                    "target_allocation": target_pct,
                    "deviation": deviation,
                    "action": "buy" if target_pct > current_pct else "sell"
                }
                actions.append(action)
                logger.info(
                    f"{symbol}: Current {current_pct:.2%}, Target {target_pct:.2%}, "
                    f"Deviation {deviation:.2%} - {action['action'].upper()}"
                )
        
        return actions
    
    def _execute_rebalancing(
        self,
        actions: List[Dict[str, Any]],
        dry_run: bool
    ) -> List[Dict[str, Any]]:
        """
        Execute rebalancing trades
        
        Args:
            actions: List of rebalancing actions
            dry_run: If True, don't place orders
            
        Returns:
            List of execution results
        """
        # Get current portfolio value
        balances = self.client.get_account_balances(self.account_number)
        total_value = balances.get("liquidationValue", 0)
        
        results = []
        
        for action in actions:
            symbol = action["symbol"]
            target_pct = action["target_allocation"]
            current_pct = action["current_allocation"]
            
            # Calculate dollar amount to trade
            target_value = total_value * target_pct
            current_value = total_value * current_pct
            trade_value = abs(target_value - current_value)
            
            try:
                result = self._execute_trade(
                    symbol,
                    action["action"],
                    trade_value,
                    dry_run
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to rebalance {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def _execute_trade(
        self,
        symbol: str,
        action: str,
        value: float,
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Execute a single rebalancing trade
        
        Args:
            symbol: Stock symbol
            action: "buy" or "sell"
            value: Dollar value to trade
            dry_run: If True, don't place order
            
        Returns:
            Trade result
        """
        # Get current quote
        quote_data = self.client.get_quote(symbol)
        quote = quote_data.get(symbol, {}).get("quote", {})
        last_price = quote.get("lastPrice", 0)
        
        if last_price == 0:
            raise ValueError(f"Invalid price for {symbol}")
        
        # Calculate shares
        shares = int(value / last_price)
        
        if shares == 0:
            return {
                "symbol": symbol,
                "status": "skipped",
                "reason": "value too small",
                "action": action,
                "value": value
            }
        
        logger.info(f"Rebalance: {action.upper()} {shares} shares of {symbol} at ~${last_price}")
        
        if dry_run:
            return {
                "symbol": symbol,
                "status": "dry_run",
                "action": action,
                "shares": shares,
                "price": last_price,
                "value": shares * last_price
            }
        
        # Create order
        order = {
            "orderType": "MARKET",
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": "BUY" if action == "buy" else "SELL",
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
            "action": action,
            "shares": shares,
            "price": last_price,
            "value": shares * last_price,
            "order_id": order_result.get("order_id")
        }
