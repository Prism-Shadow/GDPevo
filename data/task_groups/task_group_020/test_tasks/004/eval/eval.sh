#!/usr/bin/env bash
set -euo pipefail

CANDIDATE_PATH="${1:-answer.json}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/evaluate.py" "$CANDIDATE_PATH"
