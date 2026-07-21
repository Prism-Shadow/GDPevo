#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANDIDATE_PATH="${1:-"$SCRIPT_DIR/../output/answer.json"}"

python3 "$SCRIPT_DIR/evaluator.py" "$CANDIDATE_PATH"
