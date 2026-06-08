#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
CANDIDATE_PATH="${1:-"$SCRIPT_DIR/../output/answer.json"}"

python3 "$SCRIPT_DIR/eval.py" "$CANDIDATE_PATH"
