#!/usr/bin/env bash
set -euo pipefail

EVAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "$EVAL_DIR/.." && pwd)"
PREDICTION="${1:-"$TASK_DIR/output/answer.json"}"

python3 "$EVAL_DIR/evaluate.py" \
  "$TASK_DIR/eval/rubric.json" \
  "$PREDICTION"
