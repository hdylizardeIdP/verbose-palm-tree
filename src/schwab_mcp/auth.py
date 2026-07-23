#!/usr/bin/env python3
"""
OAuth authentication helper for Schwab MCP Server.

Run this once to authenticate and save tokens:
    python -m schwab_mcp.auth

After successful auth, the MCP server can run headlessly using the saved token.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schwab_app.config import Config
from schwab_app.client import SchwabClient


def main():
    """Run OAuth flow and save tokens."""
    print("Schwab MCP Server - OAuth Authentication")
    print("=" * 45)

    config = Config()

    # Account hash isn't known until after this flow completes, so don't require it.
    try:
        config.validate()
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    print(f"\nAPI Key: {config.api_key[:8]}...")
    print(f"Callback URL: {config.callback_url}")
    print(f"Token path: {config.token_path}")

    print("\nInitiating OAuth flow...")
    print("You'll be given a URL to open, then asked to paste the")
    print("redirect URL back here after logging in to Schwab.\n")

    try:
        client = SchwabClient(
            config.api_key,
            config.app_secret,
            config.callback_url,
            config.token_path,
        )
        client.authenticate()
        print("\nAuthentication successful!")
        print(f"Token saved to: {config.token_path}")
        print("\nYou can now run the MCP server headlessly.")

    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
