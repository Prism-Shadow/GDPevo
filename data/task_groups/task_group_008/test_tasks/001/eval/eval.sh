#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
  prediction="$(dirname "$0")/../output/answer.json"
elif [ "$#" -eq 1 ]; then
  prediction="$1"
else
  echo "Usage: eval.sh [prediction.json]" >&2
  exit 2
fi

python3 "$(dirname "$0")/evaluate.py" "$prediction"
