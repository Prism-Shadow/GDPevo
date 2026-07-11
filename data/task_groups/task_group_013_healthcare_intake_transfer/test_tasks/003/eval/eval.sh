#!/usr/bin/env bash
set -euo pipefail

ANSWER_PATH="${1:-output/answer.json}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/evaluator.py" "$ANSWER_PATH"
