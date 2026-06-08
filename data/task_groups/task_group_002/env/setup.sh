#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ ! -f data/business_data.json || ! -f data/manifest.json ]]; then
  python3 generate_data.py
fi

PORT="${PORT:-8002}"
export PORT
exec python3 server.py
