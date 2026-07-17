#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  printf '%s\n' '{"score":0.0,"error":"usage: eval.sh <prediction.json>"}'
  exit 0
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/evaluator.py" "$1"
