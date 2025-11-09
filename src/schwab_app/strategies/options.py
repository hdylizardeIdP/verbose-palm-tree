"""
Options trading strategy
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from schwab_app.client import SchwabClient

logger = logging.getLogger(__name__)


class OptionsStrategy:
    """Options trading strategy implementation"""
    
    def __init__(self, client: SchwabClient, account_number: str):
        """
        Initialize options strategy
        
        Args:
            client: Schwab API client
            account_number: Account number
        """
        self.client = client
        self.account_number = account_number
    
    def sell_covered_calls(
        self,
        positions: Optional[List[str]] = None,
        days_to_expiry: int = 30,
        otm_percentage: float = 0.05,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Sell covered calls on existing positions
        
        Args:
            positions: List of symbols to sell calls on (None = all positions)
            days_to_expiry: Target days to expiration
            otm_percentage: How far out of the money (e.g., 0.05 for 5% above current price)
            dry_run: If True, don't place orders
            
        Returns:
            List of covered call results
        """
        logger.info(f"Executing covered call strategy ({days_to_expiry} DTE, {otm_percentage*100}% OTM)")
        
        try:
            # Get current positions
            current_positions = self.client.get_positions(self.account_number)
            
            results = []
            
            for position in current_positions:
                instrument = position.get("instrument", {})
                symbol = instrument.get("symbol", "")
                long_quantity = position.get("longQuantity", 0)
                
                # Skip if not equity or insufficient shares
                if instrument.get("assetType") != "EQUITY" or long_quantity < 100:
                    continue
                
                # Skip if not in target list
                if positions and symbol not in positions:
                    continue
                
                try:
                    result = self._sell_covered_call(
                        symbol,
                        int(long_quantity / 100),  # Number of contracts (1 contract = 100 shares)
                        days_to_expiry,
                        otm_percentage,
                        dry_run
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to sell covered call on {symbol}: {e}")
                    results.append({
                        "symbol": symbol,
                        "status": "failed",
                        "error": str(e)
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to execute covered call strategy: {e}")
            raise
    
    def _sell_covered_call(
        self,
        symbol: str,
        contracts: int,
        days_to_expiry: int,
        otm_percentage: float,
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Sell a covered call on a specific symbol
        
        Args:
            symbol: Stock symbol
            contracts: Number of contracts to sell
            days_to_expiry: Target days to expiration
            otm_percentage: Out of the money percentage
            dry_run: If True, don't place order
            
        Returns:
            Covered call result
        """
        # Get current stock price
        quote_data = self.client.get_quote(symbol)
        quote = quote_data.get(symbol, {}).get("quote", {})
        stock_price = quote.get("lastPrice", 0)
        
        if stock_price == 0:
            raise ValueError(f"Invalid price for {symbol}")
        
        # Calculate target strike price
        target_strike = stock_price * (1 + otm_percentage)
        
        # Get option chain
        option_chain = self.client.get_option_chain(
            symbol,
            contractType="CALL",
            strikeCount=10,
            optionType="S"  # Standard options
        )
        
        # Find suitable call option
        suitable_option = self._find_suitable_call(
            option_chain,
            target_strike,
            days_to_expiry
        )
        
        if not suitable_option:
            return {
                "symbol": symbol,
                "status": "skipped",
                "reason": "no suitable option found"
            }
        
        option_symbol = suitable_option["symbol"]
        strike = suitable_option["strike"]
        expiry = suitable_option["expiry"]
        bid = suitable_option["bid"]
        
        premium = bid * 100 * contracts  # Premium received
        
        logger.info(
            f"Covered call: SELL {contracts} {symbol} {strike}C {expiry} "
            f"for ${premium:.2f} premium"
        )
        
        if dry_run:
            return {
                "symbol": symbol,
                "status": "dry_run",
                "contracts": contracts,
                "option_symbol": option_symbol,
                "strike": strike,
                "expiry": expiry,
                "premium": premium
            }
        
        # Create sell-to-open order for covered call
        order = {
            "orderType": "NET_CREDIT",
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "price": bid,
            "orderLegCollection": [
                {
                    "instruction": "SELL_TO_OPEN",
                    "quantity": contracts,
                    "instrument": {
                        "symbol": option_symbol,
                        "assetType": "OPTION"
                    }
                }
            ]
        }
        
        # Place order
        order_result = self.client.place_order(self.account_number, order)
        
        return {
            "symbol": symbol,
            "status": "success",
            "contracts": contracts,
            "option_symbol": option_symbol,
            "strike": strike,
            "expiry": expiry,
            "premium": premium,
            "order_id": order_result.get("order_id")
        }
    
    def _find_suitable_call(
        self,
        option_chain: Dict[str, Any],
        target_strike: float,
        target_days: int
    ) -> Optional[Dict[str, Any]]:
        """
        Find a suitable call option from the chain
        
        Args:
            option_chain: Option chain data
            target_strike: Target strike price
            target_days: Target days to expiration
            
        Returns:
            Option data if found, None otherwise
        """
        call_map = option_chain.get("callExpDateMap", {})
        
        best_option = None
        best_score = float('inf')
        
        for exp_date_str, strikes in call_map.items():
            # Parse expiration date
            exp_date = exp_date_str.split(":")[0]
            
            for strike_str, options in strikes.items():
                strike = float(strike_str)
                
                # Skip if strike is too far from target
                if abs(strike - target_strike) / target_strike > 0.10:  # Within 10%
                    continue
                
                for option in options:
                    bid = option.get("bid", 0)
                    
                    # Skip if no bid
                    if bid <= 0:
                        continue
                    
                    # Calculate score (prefer closer to target strike and expiry)
                    strike_diff = abs(strike - target_strike)
                    score = strike_diff
                    
                    if score < best_score:
                        best_score = score
                        best_option = {
                            "symbol": option.get("symbol"),
                            "strike": strike,
                            "expiry": exp_date,
                            "bid": bid,
                            "ask": option.get("ask", 0)
                        }
        
        return best_option
    
    def buy_protective_puts(
        self,
        positions: Optional[List[str]] = None,
        days_to_expiry: int = 30,
        otm_percentage: float = 0.05,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Buy protective puts on existing positions
        
        Args:
            positions: List of symbols to protect (None = all positions)
            days_to_expiry: Target days to expiration
            otm_percentage: How far out of the money (e.g., 0.05 for 5% below current price)
            dry_run: If True, don't place orders
            
        Returns:
            List of protective put results
        """
        logger.info(f"Executing protective put strategy ({days_to_expiry} DTE, {otm_percentage*100}% OTM)")
        
        try:
            current_positions = self.client.get_positions(self.account_number)
            
            results = []
            
            for position in current_positions:
                instrument = position.get("instrument", {})
                symbol = instrument.get("symbol", "")
                long_quantity = position.get("longQuantity", 0)
                
                if instrument.get("assetType") != "EQUITY" or long_quantity < 100:
                    continue
                
                if positions and symbol not in positions:
                    continue
                
                try:
                    result = self._buy_protective_put(
                        symbol,
                        int(long_quantity / 100),
                        days_to_expiry,
                        otm_percentage,
                        dry_run
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to buy protective put for {symbol}: {e}")
                    results.append({
                        "symbol": symbol,
                        "status": "failed",
                        "error": str(e)
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to execute protective put strategy: {e}")
            raise
    
    def _buy_protective_put(
        self,
        symbol: str,
        contracts: int,
        days_to_expiry: int,
        otm_percentage: float,
        dry_run: bool
    ) -> Dict[str, Any]:
        """
        Buy a protective put for a specific symbol
        
        Args:
            symbol: Stock symbol
            contracts: Number of contracts to buy
            days_to_expiry: Target days to expiration
            otm_percentage: Out of the money percentage
            dry_run: If True, don't place order
            
        Returns:
            Protective put result
        """
        # Get current stock price
        quote_data = self.client.get_quote(symbol)
        quote = quote_data.get(symbol, {}).get("quote", {})
        stock_price = quote.get("lastPrice", 0)
        
        if stock_price == 0:
            raise ValueError(f"Invalid price for {symbol}")
        
        # Calculate target strike price (below current price)
        target_strike = stock_price * (1 - otm_percentage)
        
        # Get option chain
        option_chain = self.client.get_option_chain(
            symbol,
            contractType="PUT",
            strikeCount=10,
            optionType="S"
        )
        
        # Find suitable put option
        suitable_option = self._find_suitable_put(
            option_chain,
            target_strike,
            days_to_expiry
        )
        
        if not suitable_option:
            return {
                "symbol": symbol,
                "status": "skipped",
                "reason": "no suitable option found"
            }
        
        option_symbol = suitable_option["symbol"]
        strike = suitable_option["strike"]
        expiry = suitable_option["expiry"]
        ask = suitable_option["ask"]
        
        cost = ask * 100 * contracts  # Cost of protection
        
        logger.info(
            f"Protective put: BUY {contracts} {symbol} {strike}P {expiry} "
            f"for ${cost:.2f}"
        )
        
        if dry_run:
            return {
                "symbol": symbol,
                "status": "dry_run",
                "contracts": contracts,
                "option_symbol": option_symbol,
                "strike": strike,
                "expiry": expiry,
                "cost": cost
            }
        
        # Create buy-to-open order for protective put
        order = {
            "orderType": "NET_DEBIT",
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "price": ask,
            "orderLegCollection": [
                {
                    "instruction": "BUY_TO_OPEN",
                    "quantity": contracts,
                    "instrument": {
                        "symbol": option_symbol,
                        "assetType": "OPTION"
                    }
                }
            ]
        }
        
        # Place order
        order_result = self.client.place_order(self.account_number, order)
        
        return {
            "symbol": symbol,
            "status": "success",
            "contracts": contracts,
            "option_symbol": option_symbol,
            "strike": strike,
            "expiry": expiry,
            "cost": cost,
            "order_id": order_result.get("order_id")
        }
    
    def _find_suitable_put(
        self,
        option_chain: Dict[str, Any],
        target_strike: float,
        target_days: int
    ) -> Optional[Dict[str, Any]]:
        """
        Find a suitable put option from the chain
        
        Args:
            option_chain: Option chain data
            target_strike: Target strike price
            target_days: Target days to expiration
            
        Returns:
            Option data if found, None otherwise
        """
        put_map = option_chain.get("putExpDateMap", {})
        
        best_option = None
        best_score = float('inf')
        
        for exp_date_str, strikes in put_map.items():
            exp_date = exp_date_str.split(":")[0]
            
            for strike_str, options in strikes.items():
                strike = float(strike_str)
                
                if abs(strike - target_strike) / target_strike > 0.10:
                    continue
                
                for option in options:
                    ask = option.get("ask", 0)
                    
                    if ask <= 0:
                        continue
                    
                    strike_diff = abs(strike - target_strike)
                    score = strike_diff
                    
                    if score < best_score:
                        best_score = score
                        best_option = {
                            "symbol": option.get("symbol"),
                            "strike": strike,
                            "expiry": exp_date,
                            "bid": option.get("bid", 0),
                            "ask": ask
                        }
        
        return best_option
