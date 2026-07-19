#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo '{"score":0,"points":0,"max_score":17,"error":"usage: eval.sh /path/to/candidate_answer.json"}'
  exit 0
fi

python3 "$(dirname "$0")/eval.py" "$1"
