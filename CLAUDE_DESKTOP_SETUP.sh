#!/bin/bash
# Setup script for Claude Desktop MCP configuration
# This script adds the Schwab MCP server to Claude Desktop

set -e

REPO_PATH="/Users/david/verbose-palm-tree"
CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

echo "🔧 Schwab MCP Server - Claude Desktop Setup"
echo "=========================================="

# Check if Claude Desktop config directory exists
if [ ! -d "$CONFIG_DIR" ]; then
    echo "❌ Claude Desktop config directory not found: $CONFIG_DIR"
    echo "   Make sure Claude Desktop has been run at least once."
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  Creating new Claude Desktop config..."
    mkdir -p "$CONFIG_DIR"
    echo '{"mcpServers": {}}' > "$CONFIG_FILE"
fi

# Backup existing config
echo "📋 Backing up existing config..."
cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%s)"
echo "   ✅ Backup created: $CONFIG_FILE.backup.*"

# Add Schwab MCP server to config
echo "🔌 Configuring Schwab MCP server..."

python3 << 'PYTHON_SCRIPT'
import json
import sys
from pathlib import Path

config_file = Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
repo_path = "/Users/david/verbose-palm-tree"

# Read existing config
with open(config_file, 'r') as f:
    config = json.load(f)

# Ensure mcpServers key exists
if "mcpServers" not in config:
    config["mcpServers"] = {}

# Add/update Schwab server
# NOTE: the "mcp" package requires Python 3.10+, but macOS ships python3 at
# 3.9. Use the project venv (set up via `python3.12 -m venv .venv` +
# `.venv/bin/pip install -r requirements.txt`) and set PYTHONPATH explicitly
# since Claude Desktop doesn't reliably honor "cwd" for module resolution.
config["mcpServers"]["schwab"] = {
    "command": f"{repo_path}/.venv/bin/python3",
    "args": ["-m", "schwab_mcp.server"],
    "cwd": f"{repo_path}/src",
    "env": {
        "PYTHONPATH": f"{repo_path}/src"
    }
}

# Write back config
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print("   ✅ Schwab MCP server added to config")
PYTHON_SCRIPT

# Display next steps
echo ""
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Quit Claude Desktop completely (⌘Q)"
echo "2. Reopen Claude Desktop"
echo "3. Ask Claude: 'What is the market cap of AAPL?'"
echo ""
echo "Configuration file:"
echo "   $CONFIG_FILE"
echo ""
echo "To view the config:"
echo "   cat \"$CONFIG_FILE\""
echo ""
echo "To restore backup (if needed):"
echo "   cp \"$CONFIG_FILE.backup.*\" \"$CONFIG_FILE\""
echo ""
