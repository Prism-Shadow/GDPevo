#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -gt 0 ]]; then
  CANDIDATE_PATH="$1"
else
  CANDIDATE_PATH="${SCRIPT_DIR}/../output/answer.json"
fi

python3 "${SCRIPT_DIR}/eval.py" "${CANDIDATE_PATH}"
