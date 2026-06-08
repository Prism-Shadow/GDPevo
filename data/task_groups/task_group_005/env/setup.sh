#!/usr/bin/env sh
set -eu

PORT="${1:-8005}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

cd "$SCRIPT_DIR"

if [ ! -f "manifest.json" ] || [ ! -f "data/claims.json" ]; then
  python generate_data.py
fi

python server.py "$PORT"
