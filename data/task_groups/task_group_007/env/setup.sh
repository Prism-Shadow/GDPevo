#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT="${TASK_ENV_PORT:-${PORT:-9007}}"

if [ ! -f "data/manifest.json" ]; then
  "$PYTHON_BIN" generate_data.py
fi

exec "$PYTHON_BIN" server.py --host "$HOST" --port "$PORT"
