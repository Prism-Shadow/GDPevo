#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo '{"score":0,"max_score":1,"error":"usage: eval.sh /path/to/prediction.json"}'
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/evaluator.py" "$1"
