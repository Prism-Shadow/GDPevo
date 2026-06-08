#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SUBMISSION_PATH="${1:-${SUBMISSION_PATH:-${TASK_DIR}/output/answer.json}}"

python3 "${SCRIPT_DIR}/evaluate.py" "${SUBMISSION_PATH}"
