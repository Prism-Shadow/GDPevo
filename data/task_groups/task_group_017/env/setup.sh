#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-8057}"
HOST="${TASK_ENV_HOST:-0.0.0.0}"

if [[ ! -f "${ENV_DIR}/manifest.json" ]] || [[ ! -f "${ENV_DIR}/data/generated/matters.json" ]]; then
  python3 "${ENV_DIR}/generate_data.py" >/dev/null
fi

TASK_ENV_HOST="${HOST}" PORT="${PORT}" exec python3 "${ENV_DIR}/server.py"
