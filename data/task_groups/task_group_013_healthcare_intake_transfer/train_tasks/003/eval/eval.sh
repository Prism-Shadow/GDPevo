#!/usr/bin/env bash
set -euo pipefail

TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED="${TASK_DIR}/output/answer.json"
ACTUAL="${1:-${TASK_DIR}/output/answer.json}"

python3 "${TASK_DIR}/eval/evaluator.py" "${EXPECTED}" "${ACTUAL}"
