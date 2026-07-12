#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${TASK_ENV_PORT:-8007}"
HOST="${TASK_ENV_HOST:-0.0.0.0}"

cd "$SCRIPT_DIR"
python3 generate_data.py
exec python3 server.py --host "$HOST" --port "$PORT"
