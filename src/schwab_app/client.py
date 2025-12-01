"""
Schwab API client wrapper
"""
import logging
import os
from typing import Optional, List, Dict, Any, Callable
from schwab import auth, client
from schwab.client import Client
import json
from pathlib import Path

from schwab_app.utils.token_encryption import (
    TokenEncryption,
    TokenEncryptionError,
    is_encrypted_token_file,
    migrate_plain_text_tokens,
)

logger = logging.getLogger(__name__)


class SchwabClient:
    """Wrapper for Schwab API client with encrypted token storage"""

    def __init__(
        self,
        api_key: str,
        app_secret: str,
        callback_url: str,
        token_path: str,
        encryption_key: Optional[str] = None,
    ):
        """
        Initialize Schwab API client with encrypted token storage.

        Args:
            api_key: Schwab API key
            app_secret: Schwab app secret
            callback_url: OAuth callback URL
            token_path: Path to store OAuth tokens (will be encrypted)
            encryption_key: Encryption key for token storage. If None, uses
                          SCHWAB_TOKEN_ENCRYPTION_KEY environment variable.

        Raises:
            TokenEncryptionError: If encryption key is not available.
        """
        self.api_key = api_key
        self.app_secret = app_secret
        self.callback_url = callback_url
        self.token_path = Path(token_path)
        self._client: Optional[Client] = None

        # Initialize token encryption
        self._encryption = TokenEncryption(encryption_key)

        # Check for and migrate plain text tokens if they exist
        self._migrate_existing_tokens()

    def _migrate_existing_tokens(self) -> None:
        """Migrate existing plain text tokens to encrypted format."""
        if not self.token_path.exists():
            return

        if not is_encrypted_token_file(self.token_path):
            logger.warning(
                "Found plain text token file. Migrating to encrypted format..."
            )
            try:
                # Read the plain text tokens
                with open(self.token_path, 'r') as f:
                    token_data = json.load(f)

                # Encrypt and save
                self._encryption.save_encrypted_tokens(token_data, self.token_path)
                logger.info("Successfully migrated tokens to encrypted format")
            except Exception as e:
                logger.error(f"Failed to migrate tokens: {e}")
                raise TokenEncryptionError(
                    f"Failed to migrate plain text tokens to encrypted format: {e}"
                )

    def _create_token_write_callback(self) -> Callable[[dict], None]:
        """Create a callback function for writing tokens with encryption."""
        def write_token(token_data: dict) -> None:
            self._encryption.save_encrypted_tokens(token_data, self.token_path)
        return write_token

    def _load_tokens(self) -> Optional[dict]:
        """Load and decrypt tokens from file."""
        if not self.token_path.exists():
            return None
        return self._encryption.load_encrypted_tokens(self.token_path)

    def authenticate(self) -> Client:
        """
        Authenticate with Schwab API using encrypted token storage.

        Returns:
            Authenticated Schwab client

        Raises:
            TokenEncryptionError: If token encryption/decryption fails.
            Exception: If authentication fails.
        """
        try:
            # Try to use existing encrypted token
            if self.token_path.exists():
                logger.info("Loading encrypted token file")
                try:
                    token_data = self._load_tokens()
                    if token_data:
                        # Create a temporary decrypted file for schwab-py
                        # Then immediately re-encrypt after client creation
                        import tempfile
                        with tempfile.NamedTemporaryFile(
                            mode='w', suffix='.json', delete=False
                        ) as tmp:
                            json.dump(token_data, tmp)
                            tmp_path = tmp.name

                        try:
                            self._client = auth.client_from_token_file(
                                tmp_path,
                                self.api_key,
                                self.app_secret,
                                token_write_func=self._create_token_write_callback()
                            )
                        finally:
                            # Always clean up temp file
                            Path(tmp_path).unlink(missing_ok=True)
                except TokenEncryptionError as e:
                    logger.error(f"Failed to decrypt tokens: {e}")
                    raise
            else:
                # Perform OAuth flow with encrypted token storage
                logger.info("Performing OAuth authentication")
                import tempfile
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.json', delete=False
                ) as tmp:
                    tmp_path = tmp.name

                try:
                    self._client = auth.client_from_manual_flow(
                        self.api_key,
                        self.app_secret,
                        self.callback_url,
                        tmp_path,
                        token_write_func=self._create_token_write_callback()
                    )
                    # Also encrypt the initial token file created by manual flow
                    if Path(tmp_path).exists():
                        with open(tmp_path, 'r') as f:
                            initial_tokens = json.load(f)
                        self._encryption.save_encrypted_tokens(
                            initial_tokens, self.token_path
                        )
                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)

            logger.info("Successfully authenticated with Schwab API")
            return self._client
        except TokenEncryptionError:
            raise
        except Exception as e:
            # Sanitize error message to avoid exposing sensitive details
            logger.error("Authentication failed")
            raise RuntimeError("Authentication failed. Check credentials and try again.")
    
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
