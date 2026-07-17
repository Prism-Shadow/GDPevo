#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -eq 0 ]]; then
  set -- "$SCRIPT_DIR/../output/answer.json"
fi
python3 "$SCRIPT_DIR/evaluator.py" "$@"
