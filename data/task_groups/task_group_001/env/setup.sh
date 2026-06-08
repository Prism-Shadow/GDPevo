#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-${1:-8067}}"

cd "$SCRIPT_DIR"

if [[ ! -f "$SCRIPT_DIR/data/harborcrm_data.json" || ! -f "$SCRIPT_DIR/data/manifest.json" ]]; then
  python3 "$SCRIPT_DIR/generate_data.py"
fi

exec python3 "$SCRIPT_DIR/server.py" --port "$PORT"
