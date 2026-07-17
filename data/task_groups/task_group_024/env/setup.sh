#!/bin/sh
set -eu

BASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$BASE_DIR"

BIND="${TASK_ENV_BIND:-0.0.0.0}"
PORT="${TASK_ENV_PORT:-9024}"

python3 - "$BIND" "$PORT" <<'PY'
import ipaddress
import sys

try:
    ipaddress.IPv4Address(sys.argv[1])
    port = int(sys.argv[2])
    if not 1 <= port <= 65535:
        raise ValueError
except ValueError:
    raise SystemExit("invalid TASK_ENV_BIND or TASK_ENV_PORT")
PY

case "${1:-}" in
    --regenerate)
        shift
        find "$BASE_DIR/data" -type f -exec chmod u+w {} +
        chmod u+w "$BASE_DIR/manifest.json"
        python3 "$BASE_DIR/generate_data.py" "$@"
        find "$BASE_DIR/data" -type f -exec chmod a-w {} +
        chmod a-w "$BASE_DIR/manifest.json"
        ;;
    --check)
        shift
        exec python3 - "$BASE_DIR" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
for relative in manifest["generated_files"]:
    payload = json.loads((root / relative).read_text(encoding="utf-8"))
    key = Path(relative).stem
    expected = manifest["record_counts"].get(key)
    if expected is not None and len(payload) != expected:
        raise SystemExit(f"{relative}: expected {expected} records, found {len(payload)}")
print("environment data check passed")
PY
        ;;
    "")
        ;;
    *)
        echo "Usage: setup.sh [--regenerate|--check]" >&2
        exit 2
        ;;
esac

if [ ! -f "data/work_items.json" ] || [ ! -f "data/status_history.json" ] || [ ! -f "manifest.json" ]; then
    python3 "$BASE_DIR/generate_data.py" >/dev/null
fi

export TASK_ENV_BIND="$BIND"
export TASK_ENV_PORT="$PORT"

echo "Engineering operations environment listening on ${BIND}:${PORT}"
exec python3 "$BASE_DIR/server.py" --host "$BIND" --port "$PORT"
