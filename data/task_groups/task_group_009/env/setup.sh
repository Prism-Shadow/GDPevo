#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT_VALUE="${1:-${PORT:-8047}}"

if [ ! -f "${SCRIPT_DIR}/data/manifest.json" ]; then
  python3 "${SCRIPT_DIR}/generate_data.py"
fi

python3 "${SCRIPT_DIR}/server.py" --host 127.0.0.1 --port "${PORT_VALUE}"
