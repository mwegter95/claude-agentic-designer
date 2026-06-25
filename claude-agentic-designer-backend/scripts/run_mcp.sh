#!/usr/bin/env bash
# Run the MCP server for manual inspection (Claude Desktop launches it itself).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Use the MCP Inspector if available; otherwise run plain stdio.
if command -v mcp >/dev/null 2>&1; then
  exec mcp dev mcp_server.py
else
  exec python mcp_server.py
fi
