#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ENV_DIR"

if [[ ! -f payer_ops.db || "${TASK_ENV_REGENERATE:-0}" == "1" ]]; then
  python3 generate_data.py
fi

HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
PORT_VALUE="${PORT:-${TASK_ENV_PORT:-9014}}"
USERNAME="payer_ops_solver"
PASSWORD="revcycle_sql_014"

echo "Listen address: http://${HOST}:${PORT_VALUE}"
echo "Basic Auth: ${USERNAME} / ${PASSWORD}"
exec python3 server.py --db payer_ops.db --host "$HOST" --port "$PORT_VALUE"
