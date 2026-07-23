#!/usr/bin/env python3
"""
Account hash lookup for Schwab MCP Server.

Schwab API calls take an account *hash*, not the brokerage account number.
Run this after authenticating to find the hash for SCHWAB_ACCOUNT_NUMBER:

    python -m schwab_mcp.accounts

Requires an existing token, so run schwab_mcp.auth first.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from schwab_app.config import Config
from schwab_app.client import SchwabClient


def main():
    """List account numbers and their API hashes."""
    print("Schwab MCP Server - Account Hashes")
    print("=" * 45)

    config = Config()

    try:
        config.validate()
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    # Don't let a missing token silently kick off an interactive OAuth flow.
    if not Path(config.token_path).exists():
        print(f"\nError: No token found at {config.token_path}")
        print("Authenticate first:  python -m schwab_mcp.auth")
        sys.exit(1)

    try:
        client = SchwabClient(
            config.api_key,
            config.app_secret,
            config.callback_url,
            config.token_path,
            encryption_key=config.token_encryption_key,
        )
        response = client.get_client().get_account_numbers()
        response.raise_for_status()
        accounts = response.json()

    except Exception as e:
        print(f"\nFailed to fetch accounts: {e}")
        sys.exit(1)

    if not accounts:
        print("\nNo accounts found for this token.")
        sys.exit(1)

    print(f"\nFound {len(accounts)} account(s):\n")
    for account in accounts:
        print(f"  Account: {account['accountNumber']}")
        print(f"  Hash:    {account['hashValue']}\n")

    print("Set SCHWAB_ACCOUNT_NUMBER in your .env to the Hash value above.")


if __name__ == "__main__":
    main()
