#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo '{"score":0,"max_score":1,"error":"usage: eval.sh /path/to/answer.json"}'
  exit 0
fi

python3 "$(dirname "$0")/eval.py" "$1"
