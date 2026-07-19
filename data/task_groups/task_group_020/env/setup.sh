#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON:-python3}"

if [ ! -f "data/ma_workbench.db" ]; then
  "$PYTHON_BIN" generate_data.py
fi

exec "$PYTHON_BIN" app.py
