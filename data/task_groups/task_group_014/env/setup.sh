#!/usr/bin/env sh
set -eu

if [ ! -f "data/northstar_pa.sqlite" ]; then
  "${PYTHON_BIN:-python3}" generate_data.py
fi

exec "${PYTHON_BIN:-python3}" app.py
