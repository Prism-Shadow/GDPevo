#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-${TASK_ENV_PORT:-${PORT:-9020}}}"
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_FILE="$SCRIPT_DIR/data/dealdesk.json"

if [ ! -f "$DATA_FILE" ]; then
  echo "Generating Aster Legal Deal Desk data with seed 20020..."
  python3 "$SCRIPT_DIR/generate_data.py"
fi

echo "Starting Aster Legal Deal Desk"
echo "Listen address: http://${HOST}:${PORT}"
echo "Pages: /, /deals, /deals/<deal_id>, /documents/<doc_id>, /policies, /policies/<policy_id>, /benchmarks, /clauses/compare?deal_id=<deal_id>"
echo "API: /api/health, /api/deals, /api/deals/<deal_id>, /api/documents/<doc_id>, /api/policies, /api/policies/<policy_id>, /api/clauses?deal_id=<deal_id>, /api/benchmarks, /api/search?q=<query>"

TASK_ENV_BIND="${HOST}" TASK_ENV_PORT="${PORT}" exec python3 "$SCRIPT_DIR/server.py" "$PORT"
