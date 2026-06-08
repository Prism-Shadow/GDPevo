#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 generate_data.py
PORT="${PORT:-8057}"
HOST="${HOST:-127.0.0.1}"
python3 server.py --host "$HOST" --port "$PORT"
