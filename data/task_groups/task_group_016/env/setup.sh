#!/bin/sh
set -eu

cd /app
DB_PATH="${TASK_ENV_DB:-/app/generated/clinic.sqlite3}"

if [ ! -f "$DB_PATH" ]; then
  python /app/generate_data.py --db "$DB_PATH"
fi

exec python /app/app.py
