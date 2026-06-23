#!/usr/bin/env bash
# Start the Claude Agentic Designer event/orchestration server.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

HOST="${CLAUDE_DESIGNER_HOST:-127.0.0.1}"
PORT="${CLAUDE_DESIGNER_PORT:-8787}"

if [[ ! -d .venv ]]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q --disable-pip-version-check -r requirements.txt

echo "Server on http://${HOST}:${PORT}  (SSE: /api/events/stream)"
exec uvicorn server.app:app --host "${HOST}" --port "${PORT}"
