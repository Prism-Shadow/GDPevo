#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-${PORT:-8067}}"

cd "$ROOT_DIR"
export PYTHONDONTWRITEBYTECODE=1
python3 generate_data.py > /dev/null

echo "PeopleOps Console"
echo "URL: http://127.0.0.1:${PORT}/"
echo "Login: ops.lead@peopleops.local / PeopleOps#2026"
echo "Health: http://127.0.0.1:${PORT}/health"
echo "Press Ctrl+C to stop."

exec python3 app.py "$PORT"
