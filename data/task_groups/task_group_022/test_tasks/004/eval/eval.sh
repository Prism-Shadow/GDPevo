#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
CANDIDATE_PATH="${1:-}"

exec python3 "$SCRIPT_DIR/evaluator.py" "$CANDIDATE_PATH"
