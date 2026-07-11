#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ENV_DIR"

if [ ! -f "data/ehr_quality_data.json" ]; then
  python3 generate_data.py
fi

PORT="${TASK_ENV_PORT:-8007}"
HOST="${TASK_ENV_HOST:-0.0.0.0}"

echo "Starting EHR quality governance environment"
echo "Listen address: http://${HOST}:${PORT}"

TASK_ENV_HOST="$HOST" TASK_ENV_PORT="$PORT" python3 server.py
