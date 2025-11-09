"""
Schwab API client wrapper
"""
import logging
from typing import Optional, List, Dict, Any
from schwab import auth, client
from schwab.client import Client
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class SchwabClient:
    """Wrapper for Schwab API client"""
    
    def __init__(self, api_key: str, app_secret: str, callback_url: str, token_path: str):
        """
        Initialize Schwab API client
        
        Args:
            api_key: Schwab API key
            app_secret: Schwab app secret
            callback_url: OAuth callback URL
            token_path: Path to store OAuth tokens
        """
        self.api_key = api_key
        self.app_secret = app_secret
        self.callback_url = callback_url
        self.token_path = Path(token_path)
        self._client: Optional[Client] = None
    
    def authenticate(self) -> Client:
        """
        Authenticate with Schwab API
        
        Returns:
            Authenticated Schwab client
        """
        try:
            # Try to use existing token
            if self.token_path.exists():
                logger.info("Using existing token file")
                self._client = auth.client_from_token_file(
                    self.token_path,
                    self.api_key,
                    self.app_secret
                )
            else:
                # Perform OAuth flow
                logger.info("Performing OAuth authentication")
                self._client = auth.client_from_manual_flow(
                    self.api_key,
                    self.app_secret,
                    self.callback_url,
                    self.token_path
                )
            
            logger.info("Successfully authenticated with Schwab API")
            return self._client
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def get_client(self) -> Client:
        """Get authenticated client, authenticating if necessary"""
        if self._client is None:
            self.authenticate()
        return self._client
    
    def get_account_info(self, account_number: str) -> Dict[str, Any]:
        """
        Get account information
        
        Args:
            account_number: Account number (hash)
            
        Returns:
            Account information dictionary
        """
        try:
            client = self.get_client()
            response = client.get_account(account_number)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise
    
    def get_account_balances(self, account_number: str) -> Dict[str, Any]:
        """
        Get account balances
        
        Args:
            account_number: Account number (hash)
            
        Returns:
            Balance information
        """
        try:
            account_info = self.get_account_info(account_number)
            balances = account_info.get("securitiesAccount", {}).get("currentBalances", {})
            return balances
        except Exception as e:
            logger.error(f"Failed to get account balances: {e}")
            raise
    
    def get_positions(self, account_number: str) -> List[Dict[str, Any]]:
        """
        Get current positions
        
        Args:
            account_number: Account number (hash)
            
        Returns:
            List of positions
        """
        try:
            account_info = self.get_account_info(account_number)
            positions = account_info.get("securitiesAccount", {}).get("positions", [])
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get quote for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote information
        """
        try:
            client = self.get_client()
            response = client.get_quote(symbol)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get quotes for multiple symbols
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary of quotes
        """
        try:
            client = self.get_client()
            response = client.get_quotes(symbols)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get quotes: {e}")
            raise
    
    def place_order(self, account_number: str, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            account_number: Account number (hash)
            order: Order specification
            
        Returns:
            Order response
        """
        try:
            client = self.get_client()
            response = client.place_order(account_number, order)
            response.raise_for_status()
            
            # Get order ID from Location header
            location = response.headers.get('Location', '')
            order_id = location.split('/')[-1] if location else None
            
            logger.info(f"Order placed successfully. Order ID: {order_id}")
            return {"order_id": order_id, "status": "submitted"}
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    def get_option_chain(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Get option chain for a symbol
        
        Args:
            symbol: Stock symbol
            **kwargs: Additional parameters for option chain query
            
        Returns:
            Option chain data
        """
        try:
            client = self.get_client()
            response = client.get_option_chain(symbol, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get option chain for {symbol}: {e}")
            raise
    
    def get_orders(self, account_number: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Get orders for an account
        
        Args:
            account_number: Account number (hash)
            **kwargs: Additional query parameters
            
        Returns:
            List of orders
        """
        try:
            client = self.get_client()
            response = client.get_orders_for_account(account_number, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            raise
