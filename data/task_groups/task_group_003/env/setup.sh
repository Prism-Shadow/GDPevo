#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ "${REGENERATE:-0}" == "1" || ! -f data/support_data.json || ! -f data/manifest.json ]]; then
  python3 generate_data.py
fi

export TASK_ENV_BIND="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
export TASK_ENV_PORT="${TASK_ENV_PORT:-${PORT:-9003}}"
exec python3 server.py
