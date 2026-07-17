#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export TASK_ENV_BIND="${TASK_ENV_BIND:-0.0.0.0}"
export TASK_ENV_PORT="${TASK_ENV_PORT:-9013}"

if [[ ! -f data/clinic.db ]]; then
  python3 generate_data.py >/tmp/cedar_ridge_generate_data.log
fi

exec python3 app.py
