"""
Configuration management for Schwab Investment App
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import json
from schwab_app.utils.validation import validate_allocation, ValidationError


class Config:
    """Application configuration manager"""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            env_file: Path to .env file (optional)
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # Schwab API credentials
        self.api_key = os.getenv("SCHWAB_API_KEY", "")
        self.app_secret = os.getenv("SCHWAB_APP_SECRET", "")
        self.callback_url = os.getenv("SCHWAB_CALLBACK_URL", "https://localhost:8182")
        self.token_path = os.getenv("SCHWAB_TOKEN_PATH", ".schwab_tokens.json")
        
        # Account configuration
        self.account_number = os.getenv("SCHWAB_ACCOUNT_NUMBER", "")
        
        # Strategy configurations
        self.dca_enabled = os.getenv("DCA_ENABLED", "false").lower() == "true"
        self.dca_amount = float(os.getenv("DCA_AMOUNT", "100.0"))
        self.dca_frequency = os.getenv("DCA_FREQUENCY", "weekly")  # daily, weekly, monthly
        self.dca_symbols = os.getenv("DCA_SYMBOLS", "SPY,VOO").split(",")
        
        self.drip_enabled = os.getenv("DRIP_ENABLED", "false").lower() == "true"
        
        self.rebalance_enabled = os.getenv("REBALANCE_ENABLED", "false").lower() == "true"
        self.target_allocation = self._load_target_allocation()
        self.rebalance_threshold = float(os.getenv("REBALANCE_THRESHOLD", "0.05"))  # 5% deviation
        
        self.opportunistic_enabled = os.getenv("OPPORTUNISTIC_ENABLED", "false").lower() == "true"
        self.opportunistic_dip_threshold = float(os.getenv("OPPORTUNISTIC_DIP_THRESHOLD", "0.03"))  # 3% dip
        
        self.options_enabled = os.getenv("OPTIONS_ENABLED", "false").lower() == "true"
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "schwab_app.log")
    
    def _load_target_allocation(self) -> dict:
        """Load and validate target portfolio allocation from environment or file"""
        allocation_str = os.getenv("TARGET_ALLOCATION", "")

        if allocation_str:
            # Limit size to prevent DoS
            if len(allocation_str) > 10000:  # 10KB limit
                raise ValueError("TARGET_ALLOCATION too large (max 10KB)")

            try:
                allocation = json.loads(allocation_str)
                # Validate the allocation
                return validate_allocation(allocation)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in TARGET_ALLOCATION: {e}")
            except ValidationError as e:
                raise ValueError(f"Invalid allocation in TARGET_ALLOCATION: {e}")

        # Default allocation (pre-validated)
        return {
            "SPY": 0.40,  # 40% S&P 500
            "QQQ": 0.30,  # 30% Nasdaq
            "IWM": 0.15,  # 15% Small Cap
            "AGG": 0.15,  # 15% Bonds
        }
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if configuration is valid
        """
        if not self.api_key:
            raise ValueError("SCHWAB_API_KEY is required")
        if not self.app_secret:
            raise ValueError("SCHWAB_APP_SECRET is required")
        return True
