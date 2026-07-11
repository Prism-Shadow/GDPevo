#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PREDICTION_PATH="${1:-${PREDICTION:-"${SCRIPT_DIR}/../output/answer.json"}}"

python3 "$SCRIPT_DIR/eval.py" "$PREDICTION_PATH"
