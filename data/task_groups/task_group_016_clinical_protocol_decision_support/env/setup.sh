#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${TASK_ENV_HOST:-0.0.0.0}"
PORT="${TASK_ENV_PORT:-${PORT:-8076}}"

if [ ! -f "${SCRIPT_DIR}/data/clinic_data.json" ]; then
  python3 "${SCRIPT_DIR}/generate_data.py"
fi

echo "ClinicProtocol API listen address: http://${HOST}:${PORT}"
TASK_ENV_HOST="${HOST}" TASK_ENV_PORT="${PORT}" exec python3 "${SCRIPT_DIR}/server.py"
