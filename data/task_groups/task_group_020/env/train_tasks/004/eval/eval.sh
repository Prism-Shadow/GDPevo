#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PREDICTION_PATH="${1:-$SCRIPT_DIR/../output/answer.json}"

python3 "$SCRIPT_DIR/evaluate.py" "$PREDICTION_PATH"
