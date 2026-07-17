#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  set -- "$SCRIPT_DIR/../output/answer.json"
elif [[ $# -ne 1 ]]; then
  echo '{"score":0,"error":"usage: eval.sh <prediction.json>","points":[]}'
  exit 2
fi

python3 "$SCRIPT_DIR/evaluator.py" "$1" "$SCRIPT_DIR/../output/answer.json"
