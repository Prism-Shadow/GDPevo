#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f "data/generated_data.json" ]; then
  python3 generate_data.py
fi

PORT="${TASK_ENV_PORT:-8073}"
HOST="${TASK_ENV_HOST:-0.0.0.0}"
echo "Northstar Care Intake Portal"
echo "Listen address: http://${HOST}:${PORT}"
echo "Login: intake.admin@northstar.example / Northstar-Intake-2026!"
TASK_ENV_HOST="${HOST}" TASK_ENV_PORT="${PORT}" python3 app.py
