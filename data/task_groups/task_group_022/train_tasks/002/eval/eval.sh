#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo '{"score":0.0,"earned_weight":0,"total_weight":16,"points":[{"id":"ERR","weight":0,"earned":0,"passed":false,"goal":"Usage: eval.sh <prediction.json>"}]}'
  exit 0
fi

python3 "$(dirname "$0")/evaluate.py" "$1"
