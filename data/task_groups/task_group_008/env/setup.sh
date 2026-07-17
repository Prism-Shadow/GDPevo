#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 generate_data.py
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT="${TASK_ENV_PORT:-${PORT:-9008}}"
exec python3 server.py --host "$HOST" --port "$PORT"
