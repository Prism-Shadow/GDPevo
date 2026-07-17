#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PORT="${TASK_ENV_PORT:-${PORT:-9019}}"
HOST="${TASK_ENV_BIND:-${TASK_ENV_HOST:-0.0.0.0}}"
REGENERATE="0"

for arg in "$@"; do
  case "$arg" in
    --regenerate)
      REGENERATE="1"
      ;;
    --port=*)
      PORT="${arg#--port=}"
      ;;
    ''|*[!0-9]*)
      echo "Usage: $0 [--regenerate] [port]" >&2
      echo "       $0 [--regenerate] --port=8057" >&2
      exit 2
      ;;
    *)
      PORT="$arg"
      ;;
  esac
done

DB_PATH="$SCRIPT_DIR/data/clrp.db"
PUBLIC_MANIFEST="$SCRIPT_DIR/data/public_manifest.json"
CONSTRUCTION_MANIFEST="$SCRIPT_DIR/data/construction_manifest.json"

if [[ "$REGENERATE" == "1" || ! -f "$DB_PATH" ]]; then
  python3 "$SCRIPT_DIR/generate_data.py"
fi

echo "Listen address: http://${HOST}:$PORT"
echo "Database: $DB_PATH"
echo "Public manifest: $PUBLIC_MANIFEST"
echo "Construction manifest: $CONSTRUCTION_MANIFEST"

exec python3 "$SCRIPT_DIR/server.py" --host "$HOST" --port "$PORT"
