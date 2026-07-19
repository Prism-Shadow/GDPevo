#!/usr/bin/env bash
set -euo pipefail

python3 "$(dirname "$0")/eval.py" "$1"
