#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

EXPECTED="${TASK_DIR}/output/answer.json"
ACTUAL="${1:-${TASK_DIR}/output/answer.json}"

python3 "${SCRIPT_DIR}/evaluator.py" "${EXPECTED}" "${ACTUAL}"
