#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PRED_PATH="${1:-$TASK_DIR/output/answer.json}"
python3 "$SCRIPT_DIR/eval.py" "$PRED_PATH"
