#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT="${TASK_ENV_PORT:-${PORT:-${1:-9012}}}"

cd "$ROOT_DIR"
export PYTHONDONTWRITEBYTECODE=1
export TASK_ENV_BIND="$HOST"
export TASK_ENV_PORT="$PORT"
python3 generate_data.py > /dev/null

exec python3 app.py "$PORT"
