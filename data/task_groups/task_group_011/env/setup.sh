#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if [ ! -f data/credit_office.db ] || [ ! -f data/public_manifest.json ]; then
  python3 generate_data.py
fi

HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT="${TASK_ENV_PORT:-${PORT:-9011}}"
exec python3 server.py --host "$HOST" --port "$PORT"
