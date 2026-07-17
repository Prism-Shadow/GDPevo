#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo '{"score":0.0,"diagnostics":["usage: eval.sh <prediction.json>"]}'
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/evaluator.py" "$1"
