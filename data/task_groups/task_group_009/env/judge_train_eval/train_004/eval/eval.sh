#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GROUP_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
PREDICTION="${1:-${SCRIPT_DIR}/../output/answer.json}"
python3 "${GROUP_DIR}/eval_common.py" "${SCRIPT_DIR}/../output/answer.json" "${SCRIPT_DIR}/config.json" "${PREDICTION}"
