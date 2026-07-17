#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  PREDICTION="$SCRIPT_DIR/../output/answer.json"
elif [[ $# -eq 1 ]]; then
  PREDICTION="$1"
else
  echo '{"error":"usage: eval.sh [prediction.json]"}'
  exit 2
fi

python3 "$SCRIPT_DIR/evaluator.py" "$PREDICTION"
