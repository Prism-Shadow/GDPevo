#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREDICTION_JSON="${1:-${PREDICTION:-"$SCRIPT_DIR/../output/answer.json"}}"

python3 "$SCRIPT_DIR/eval.py" "$PREDICTION_JSON"
