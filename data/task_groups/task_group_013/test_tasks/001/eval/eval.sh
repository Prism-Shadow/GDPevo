#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSWER_PATH="${1:-answer.json}"

python3 "$SCRIPT_DIR/evaluator.py" "$ANSWER_PATH"
