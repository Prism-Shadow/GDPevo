#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CANDIDATE_PATH="${1:-${TASK_DIR}/output/answer.json}"

python3 "$SCRIPT_DIR/evaluate.py" "$CANDIDATE_PATH"
