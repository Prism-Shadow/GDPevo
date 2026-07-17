#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREDICTION_PATH="${1:-${PREDICTION:-}}"

if [[ -z "${PREDICTION_PATH}" ]]; then
  PREDICTION_PATH="${SCRIPT_DIR}/../output/answer.json"
fi

python3 "${SCRIPT_DIR}/eval.py" "${PREDICTION_PATH}"
