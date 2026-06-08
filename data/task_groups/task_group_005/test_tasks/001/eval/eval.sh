#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
TASK_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
PREDICTION_FILE="${1:-${PREDICTION_FILE:-$TASK_DIR/output/answer.json}}"

python3 "$SCRIPT_DIR/eval.py" "$PREDICTION_FILE"
