#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT="${TASK_ENV_PORT:-${PORT:-${1:-9005}}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

cd "$SCRIPT_DIR"

if [ ! -f "manifest.json" ] || [ ! -f "data/claims.json" ]; then
  "$PYTHON_BIN" generate_data.py
fi

export TASK_ENV_BIND="$HOST"
export TASK_ENV_PORT="$PORT"
exec "$PYTHON_BIN" server.py "$PORT"
