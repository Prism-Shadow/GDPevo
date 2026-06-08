#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ "${REGENERATE:-0}" == "1" || ! -f data/support_data.json || ! -f data/manifest.json ]]; then
  python3 generate_data.py
fi

PORT="${PORT:-8057}"
echo "Starting support console API at http://127.0.0.1:${PORT}"
echo "Health endpoint: http://127.0.0.1:${PORT}/health"
exec python3 server.py
