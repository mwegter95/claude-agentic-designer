#!/usr/bin/env bash
# One-time setup for the backend on a fresh machine (macOS).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Claude Agentic Designer — backend install =="

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install from https://www.python.org or 'brew install python'." >&2
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if ! command -v soffice >/dev/null 2>&1 \
   && [[ ! -x /Applications/LibreOffice.app/Contents/MacOS/soffice ]]; then
  echo ""
  echo "WARNING: LibreOffice (soffice) not found — slide rendering will be skipped."
  echo "Install it with:  brew install --cask libreoffice"
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit it to configure Microsoft 365 if needed."
fi

echo "Done. Start the server with:  ./scripts/run_server.sh"
