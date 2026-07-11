#!/usr/bin/env bash
set -euo pipefail

TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ANSWER_PATH="${1:-"$TASK_DIR/output/answer.json"}"

python3 "$TASK_DIR/eval/evaluator.py" "$ANSWER_PATH"
