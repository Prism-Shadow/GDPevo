#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 eval.py "${1:-../output/answer.json}"
