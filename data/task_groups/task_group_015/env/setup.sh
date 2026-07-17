#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"
python3 generate_data.py >/dev/null
exec python3 app.py
