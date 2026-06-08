#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANSWER_PATH="${1:-$SCRIPT_DIR/../output/answer.json}"
python3 "$SCRIPT_DIR/eval.py" "$ANSWER_PATH"
