#!/usr/bin/env bash
# Build the Claude Desktop extension bundle (.mcpb) from this backend folder.
# The bundle is source-only: launcher.py bootstraps a venv and installs
# requirements on first run (so pywin32/Pillow build natively on the target PC),
# which means you can build this on macOS or Windows.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # backend dir
OUT="$(cd "$HERE/.." && pwd)/claude-agentic-designer.mcpb"

cd "$HERE"

if [[ ! -f manifest.json ]]; then
  echo "ERROR: manifest.json not found in $HERE" >&2
  exit 1
fi

rm -f "$OUT"

# Build the companion UI and vendor it into ./webui so the FastAPI server can
# serve it same-origin (no Node/Vite needed at runtime).
ROOT="$(cd "$HERE/.." && pwd)"
echo "Building companion UI (npm run build)..."
( cd "$ROOT" && npm run build )
rm -rf "$HERE/webui"
cp -R "$ROOT/dist" "$HERE/webui"

# Drop compiled-bytecode dirs so they don't end up in the bundle.
find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

# Zip the *contents* of the backend dir so manifest.json sits at the archive root.
zip -r -X "$OUT" . \
  -x '.venv/*' \
  -x '*__pycache__*' '*.pyc' \
  -x 'lib/*' \
  -x 'workspace/runs/*' 'workspace/logs/*' 'workspace/events.jsonl' \
  -x '*.DS_Store' \
  -x '.env' \
  -x '.deps-installed' >/dev/null

echo "Built: $OUT"
echo "Install it by double-clicking the .mcpb in Claude Desktop (Settings -> Extensions)."
