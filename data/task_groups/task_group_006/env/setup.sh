#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" generate_data.py

PORT="${PORT:-8006}"
echo "Start ProcureOps API with:"
echo "  $PYTHON_BIN server.py --host 127.0.0.1 --port $PORT"

if [[ "${1:-}" == "start" ]]; then
  exec "$PYTHON_BIN" server.py --host 127.0.0.1 --port "$PORT"
fi
