#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -gt 0 ]]; then
  python3 "$SCRIPT_DIR/evaluate.py" "$1"
else
  python3 "$SCRIPT_DIR/evaluate.py"
fi
