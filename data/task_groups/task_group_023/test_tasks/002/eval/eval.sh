#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 PREDICTION_JSON" >&2
  exit 2
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/evaluator.py" "$1"
