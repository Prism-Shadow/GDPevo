#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo '{"score":0,"points":0,"max_score":14,"error":"usage: eval.sh <candidate-answer.json>"}'
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/eval.py" "$1"
