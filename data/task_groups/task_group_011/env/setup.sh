#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if [ ! -f data/credit_office.db ] || [ ! -f data/public_manifest.json ]; then
  python3 generate_data.py
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8057}"
echo "Credit office API base URL: http://${HOST}:${PORT}"
exec python3 server.py --host "$HOST" --port "$PORT"
