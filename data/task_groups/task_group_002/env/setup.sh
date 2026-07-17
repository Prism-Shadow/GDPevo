#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ ! -f data/business_data.json || ! -f data/manifest.json ]]; then
  python3 generate_data.py
fi

HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT="${TASK_ENV_PORT:-${PORT:-9002}}"
export TASK_ENV_BIND="$HOST"
export TASK_ENV_PORT="$PORT"
export PORT="$PORT"
exec python3 server.py
