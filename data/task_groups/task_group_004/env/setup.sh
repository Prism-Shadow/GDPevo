#!/usr/bin/env sh
set -eu

ENV_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT="${TASK_ENV_PORT:-${PORT:-9004}}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found on PATH" >&2
  exit 1
fi

python3 "$ENV_DIR/generate_data.py"
exec python3 "$ENV_DIR/server.py" --host "$HOST" --port "$PORT"
