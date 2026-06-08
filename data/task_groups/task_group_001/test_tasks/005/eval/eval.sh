#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -gt 1 ]]; then
  echo '{"total_score":0,"points":[],"error":"Usage: eval.sh [prediction_json]"}'
  exit 2
fi

if [[ $# -eq 0 ]]; then
  python3 "$SCRIPT_DIR/evaluator.py"
else
  python3 "$SCRIPT_DIR/evaluator.py" "$1"
fi
