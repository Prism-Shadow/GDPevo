#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TASK_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PRED_PATH="${1:-$TASK_DIR/output/answer.json}"

python3 "$SCRIPT_DIR/evaluator.py" "$PRED_PATH"
