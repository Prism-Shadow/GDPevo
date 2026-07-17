#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT="${TASK_ENV_PORT:-${PORT:-9001}}"

cd "$SCRIPT_DIR"

if [[ ! -f "$SCRIPT_DIR/data/harborcrm_data.json" || ! -f "$SCRIPT_DIR/data/manifest.json" ]]; then
  python3 "$SCRIPT_DIR/generate_data.py"
fi

exec python3 "$SCRIPT_DIR/server.py" --host "$HOST" --port "$PORT"
