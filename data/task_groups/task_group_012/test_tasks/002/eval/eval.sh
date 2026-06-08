#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="$SCRIPT_DIR/evaluate.py"
RUBRIC="$SCRIPT_DIR/rubric.json"
ANSWER="${1:-$SCRIPT_DIR/../output/answer.json}"

python3 "$HELPER" --answer "$ANSWER" --rubric "$RUBRIC"
