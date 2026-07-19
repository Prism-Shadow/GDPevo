#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if [ "${TASK_ENV_REGENERATE:-0}" = "1" ] || [ ! -f generated/court_ops.db ]; then
  python3 generate_data.py
fi

exec python3 app.py
