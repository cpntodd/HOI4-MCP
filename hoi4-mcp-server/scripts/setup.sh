#!/usr/bin/env bash
# setup.sh — One-time setup for the HOI4 MCP Server
set -euo pipefail

echo "========================================="
echo " HOI4 MCP Server — Setup"
echo "========================================="
echo ""

# Check Python
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        major=$(echo "$ver" | cut -d. -f1)
        if [ "$major" -ge 3 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.10+ is required but not found."
    exit 1
fi
echo "[✓] Found $PYTHON ($($PYTHON --version))"

# Install the package
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "Installing hoi4-mcp-server..."
cd "$PROJECT_DIR"
$PYTHON -m pip install -e . 2>&1 | tail -1

echo ""
echo "[✓] hoi4-mcp-server installed!"

# Check for vanilla HOI4 path
VANILLA_PATH=""
for candidate in \
    "$HOME/.local/share/Steam/steamapps/common/Hearts of Iron IV" \
    "$HOME/.steam/steam/steamapps/common/Hearts of Iron IV" \
    "/mnt/Steam/steamapps/common/Hearts of Iron IV" \
    "$HOME/Library/Application Support/Steam/steamapps/common/Hearts of Iron IV"; do
    if [ -d "$candidate" ]; then
        VANILLA_PATH="$candidate"
        break
    fi
done

if [ -n "$VANILLA_PATH" ]; then
    echo ""
    echo "Vanilla HOI4 found at: $VANILLA_PATH"
    echo ""
    read -p "Build vanilla database now? This takes 1-2 minutes. [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]?$|^$ ]]; then
        echo "Building vanilla database..."
        $PYTHON -m hoi4_mcp.db.vanilla_index --vanilla-path "$VANILLA_PATH"
        echo "[✓] Vanilla database built!"
    fi
else
    echo ""
    echo "Vanilla HOI4 not auto-detected."
    echo "To build the vanilla database manually:"
    echo "  index-vanilla --vanilla-path /path/to/Hearts of Iron IV"
fi

echo ""
echo "========================================="
echo " Setup complete!"
echo "========================================="
echo ""
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"
echo "To configure the MCP server for your AI tool, add this to your"
echo "MCP client configuration (e.g., claude_desktop_config.json):"
echo ""
echo '  {'
echo '    "mcpServers": {'
echo '      "hoi4-modder": {'
echo '        "command": "'"$VENV_PYTHON"'",'
echo '        "args": ["-m", "hoi4_mcp.server",'
echo '                 "--mod-path", "/path/to/your/mod",'
echo '                 "--vanilla-db", "'"$HOME"'/.hoi4_mcp/vanilla.db"]'
echo '      }'
echo '    }'
echo '  }'
echo ""
echo "Or run manually:"
echo "  $VENV_PYTHON -m hoi4_mcp.server --mod-path /path/to/your/mod"
echo ""
