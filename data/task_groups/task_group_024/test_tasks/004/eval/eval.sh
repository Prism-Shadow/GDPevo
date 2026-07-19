#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo '{"score":0,"points":0,"max_score":12,"error":"Usage: eval.sh /path/to/answer.json","details":[]}'
  exit 1
fi

python3 "$(dirname "$0")/eval.py" "$1"
