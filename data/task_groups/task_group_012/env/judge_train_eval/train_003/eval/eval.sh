#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBMISSION="${1:-${SCRIPT_DIR}/../output/answer.json}"

python3 "${SCRIPT_DIR}/evaluate.py" \
  "${SUBMISSION}" \
  "${SCRIPT_DIR}/../output/answer.json" \
  "${SCRIPT_DIR}/rubric.json"
