#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found on PATH." >&2
  exit 1
fi

if [ ! -f "data/work_items.json" ] || [ ! -f "data/status_history.json" ] || [ ! -f "manifest.json" ]; then
  echo "Generated data missing; running generator with seed 2702401."
  python3 generate_data.py >/dev/null
fi

HOST="${TASK_ENV_HOST:-0.0.0.0}"
PORT="${TASK_ENV_PORT:-8037}"
LISTEN_URL="http://${HOST}:${PORT}"

echo "Engineering operations environment"
echo "Listen address: ${LISTEN_URL}"
echo "Endpoints:"
echo "  ${LISTEN_URL}/web/dashboard"
echo "  ${LISTEN_URL}/web/policies"
echo "  ${LISTEN_URL}/api/work-items"
echo "  ${LISTEN_URL}/api/status-history?work_item_id=<id>"
echo "  ${LISTEN_URL}/api/releases"
echo "  ${LISTEN_URL}/api/search?q=<text>"

exec python3 server.py --host "$HOST" --port "$PORT"
