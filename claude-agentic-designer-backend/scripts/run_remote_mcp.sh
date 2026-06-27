#!/usr/bin/env bash
# Expose the MCP server to the internet for the Claude-for-PowerPoint add-in.
# Starts the MCP server over HTTP (SSE) and a localtunnel with a constant subdomain.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Load .env so CLAUDE_DESIGNER_MCP_* / LT_SUBDOMAIN are available.
if [[ -f ".env" ]]; then
  set -a; # shellcheck disable=SC1091
  source .env; set +a
fi

TRANSPORT="${CLAUDE_DESIGNER_MCP_TRANSPORT:-sse}"
PORT="${CLAUDE_DESIGNER_MCP_PORT:-3333}"
SUBDOMAIN="${LT_SUBDOMAIN:-claude-agentic-designer}"

# Remote mode must NOT be stdio.
if [[ "$TRANSPORT" == "stdio" ]]; then TRANSPORT="sse"; fi
export CLAUDE_DESIGNER_MCP_TRANSPORT="$TRANSPORT"

echo "== Claude Agentic Designer - remote MCP =="
echo "Transport: $TRANSPORT   Port: $PORT   Subdomain: $SUBDOMAIN"

# Start the MCP HTTP server in the background.
python mcp_server.py &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

# Wait until it is listening.
for _ in $(seq 1 30); do
  if curl -s -o /dev/null --max-time 1 "http://127.0.0.1:${PORT}/"; then break; fi
  sleep 0.5
done

ROUTE="/sse"; [[ "$TRANSPORT" == "streamable-http" ]] && ROUTE="/mcp"
echo ""
echo "Public URL (give this to Claude's Custom Connector):"
echo "  https://${SUBDOMAIN}.loca.lt${ROUTE}"
echo ""

# Run localtunnel with the constant subdomain (npx avoids a global install).
npx --yes localtunnel --port "$PORT" --subdomain "$SUBDOMAIN"
