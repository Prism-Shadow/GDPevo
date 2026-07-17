#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANDIDATE_PATH="${1:-${ANSWER_JSON:-answer.json}}"

exec python3 "$SCRIPT_DIR/eval.py" "$CANDIDATE_PATH"
