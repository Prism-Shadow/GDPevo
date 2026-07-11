#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: ./setup.sh [PORT]

Starts the task_group_018 clerk operations environment.

PORT may be supplied as the first positional argument or with the PORT
environment variable. If neither is set, port 8000 is used.

Examples:
  ./setup.sh 8063
  PORT=8063 ./setup.sh
EOF
}

if [ "$#" -gt 1 ]; then
  usage
  exit 2
fi

HOST="${TASK_ENV_HOST:-0.0.0.0}"
PORT_VALUE="${1:-${TASK_ENV_PORT:-${PORT:-8000}}}"

case "$PORT_VALUE" in
  ''|*[!0-9]*)
    usage
    exit 2
    ;;
esac

if [ "$PORT_VALUE" -lt 1 ] || [ "$PORT_VALUE" -gt 65535 ]; then
  usage
  exit 2
fi

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

python3 "$SCRIPT_DIR/generate_data.py" >/dev/null
exec python3 "$SCRIPT_DIR/server.py" --host "$HOST" --port "$PORT_VALUE"
