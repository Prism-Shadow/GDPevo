#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${TASK_ENV_PORT:-${PORT:-9017}}"
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"

if [[ ! -f "${ENV_DIR}/manifest.json" ]] || [[ ! -f "${ENV_DIR}/data/generated/matters.json" ]]; then
  python3 "${ENV_DIR}/generate_data.py" >/dev/null
fi

TASK_ENV_BIND="${HOST}" TASK_ENV_PORT="${PORT}" exec python3 "${ENV_DIR}/server.py"
