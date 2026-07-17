#!/bin/sh
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
if [ "$#" -gt 0 ] && [ -n "$1" ]; then
  ANSWER_PATH=$1
else
  ANSWER_PATH="$SCRIPT_DIR/../output/answer.json"
fi
python3 "$SCRIPT_DIR/eval.py" "$ANSWER_PATH"
