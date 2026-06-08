#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python}"
PORT="${PORT:-8007}"
HOST="${HOST:-127.0.0.1}"

if [ ! -f "data/manifest.json" ]; then
  "$PYTHON_BIN" generate_data.py
fi

echo "Data directory: $(pwd)/data"
echo "Startup command: $PYTHON_BIN server.py --host $HOST --port $PORT"

if [ "${1:-}" = "start" ]; then
  exec "$PYTHON_BIN" server.py --host "$HOST" --port "$PORT"
fi
