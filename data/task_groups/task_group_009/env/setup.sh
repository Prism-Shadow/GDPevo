#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT_VALUE="${TASK_ENV_PORT:-${PORT:-${1:-9009}}}"

if [ ! -f "${SCRIPT_DIR}/data/manifest.json" ]; then
  python3 "${SCRIPT_DIR}/generate_data.py"
fi

exec python3 "${SCRIPT_DIR}/server.py" --host "$HOST" --port "${PORT_VALUE}"
