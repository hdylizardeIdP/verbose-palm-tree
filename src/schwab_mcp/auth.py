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

from pathlib import Path

from schwab_app.config import Config
from schwab_app.client import SchwabClient
from schwab_app.utils.logging_config import setup_logging


def main():
    """Run OAuth flow and save tokens."""
    print("Schwab MCP Server - OAuth Authentication")
    print("=" * 45)

    config = Config()

    # Surface the underlying failure through the app's standard logging setup,
    # so auth diagnostics also reach config.log_file like every other entry point.
    # LOG_LEVEL=DEBUG adds tracebacks, but also makes schwab-py log full API
    # response bodies (account numbers, balances) unredacted — avoid it on shared
    # terminals and delete the log file afterwards.
    setup_logging(config.log_level, config.log_file)

    # Account hash isn't known until after this flow completes, so don't require it.
    try:
        config.validate()
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    print(f"\nAPI Key: {config.api_key[:8]}...")
    print(f"Callback URL: {config.callback_url}")
    print(f"Token path: {config.token_path}")

    # Building a session from a stored token never contacts Schwab, so this
    # command would silently do nothing if it reused an existing token. Always
    # run the real flow, but confirm first so a stray invocation can't discard a
    # working token.
    if Path(config.token_path).exists():
        print(f"\nA token already exists at {config.token_path}.")
        print("Continuing will replace it with a newly authenticated one.")
        if input("Replace it? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Cancelled. Existing token left untouched.")
            return

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
        client.authenticate(force_oauth=True)
        print("\nAuthentication successful!")
        print(f"Token saved to: {config.token_path}")
        print("\nYou can now run the MCP server headlessly.")

    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
