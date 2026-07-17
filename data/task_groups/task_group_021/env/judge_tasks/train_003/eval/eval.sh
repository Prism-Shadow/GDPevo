#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREDICTION=${1:-answer.json}
RAW_RESULT=$(mktemp)
trap 'rm -f "$RAW_RESULT"' EXIT HUP INT TERM

if ! /bin/bash "$SCRIPT_DIR/eval_impl.sh" "$PREDICTION" >"$RAW_RESULT"; then
  :
fi

python3 "$SCRIPT_DIR/whole_point_eval.py" \
  "$PREDICTION" \
  "$SCRIPT_DIR/../output/answer.json" \
  "$RAW_RESULT"
