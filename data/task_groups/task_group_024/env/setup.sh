#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if [ "${TASK_ENV_RESET:-0}" = "1" ] || [ ! -f portfolio.db ] || [ ! -f data_manifest.json ]; then
  python3 generate_data.py
fi

exec python3 app.py
