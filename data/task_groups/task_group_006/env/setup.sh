#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" generate_data.py

HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT="${TASK_ENV_PORT:-${PORT:-9006}}"
exec "$PYTHON_BIN" server.py --host "$HOST" --port "$PORT"
