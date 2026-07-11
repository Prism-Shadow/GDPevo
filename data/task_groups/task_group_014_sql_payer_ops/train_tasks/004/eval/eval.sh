#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo '{"score":0.0,"max_score":1.0,"raw_score":0,"max_raw_score":15,"error":"usage: eval.sh /path/to/prediction.json","points":[]}'
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/evaluator.py" "$1"
