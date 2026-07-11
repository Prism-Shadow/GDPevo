#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREDICTION_PATH="${1:-}"

python3 "$SCRIPT_DIR/evaluate.py" "$PREDICTION_PATH"
