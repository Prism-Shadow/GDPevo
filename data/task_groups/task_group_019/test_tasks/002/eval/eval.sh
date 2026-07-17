#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  set -- "$SCRIPT_DIR/../output/answer.json"
elif [[ $# -ne 1 ]]; then
  python3 - <<'PY'
import json
print(json.dumps({
    "score": 0.0,
    "error": "usage: eval.sh <prediction.json>",
    "points": []
}, indent=2, sort_keys=True))
PY
  exit 0
fi

python3 "$SCRIPT_DIR/evaluator.py" "$1" "$SCRIPT_DIR/../output/answer.json"
