#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREDICTION=${1:-answer.json}

python3 "$SCRIPT_DIR/whole_point_eval.py" \
  "$PREDICTION" \
  "$SCRIPT_DIR/../output/answer.json"
