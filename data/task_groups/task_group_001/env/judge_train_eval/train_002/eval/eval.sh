#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -gt 1 ]]; then
  echo '{"total_score":0,"error":"usage: eval.sh [prediction_json]","points":[]}'
  exit 0
fi

if [[ $# -eq 1 ]]; then
  python3 "$SCRIPT_DIR/evaluate.py" "$1"
else
  python3 "$SCRIPT_DIR/evaluate.py"
fi
