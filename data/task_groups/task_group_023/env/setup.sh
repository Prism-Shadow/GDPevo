#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8000}"
HOST="${TASK_ENV_HOST:-0.0.0.0}"
ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ENV_DIR"

if [[ ! -f "manifest.json" || ! -f "web/index.html" || ! -f "web/data/state_health_long.csv" || ! -f "web/data/country_health_panel.csv" ]]; then
  python3 generate_data.py
fi

echo "Listen address: http://${HOST}:${PORT}/index.html"
TASK_ENV_HOST="${HOST}" exec python3 serve.py "$PORT"
