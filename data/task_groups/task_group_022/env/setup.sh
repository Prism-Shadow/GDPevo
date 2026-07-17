#!/bin/sh
set -eu

umask 077

BIND="${TASK_ENV_BIND:-0.0.0.0}"
PORT="${TASK_ENV_PORT:-9022}"
RUNTIME_DIR="${TASK_ENV_RUNTIME_DIR:-/var/lib/atlas}"
BASELINE="${TASK_ENV_BASELINE:-/app/atlas_baseline.sqlite3}"
DATABASE="${TASK_ENV_DATABASE:-${RUNTIME_DIR}/atlas_runtime.sqlite3}"

python - "$BIND" "$PORT" <<'PY'
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

if [ -z "${TASK_ENV_API_TOKEN:-atlas-ops-token-022}" ] || [ -z "${TASK_ENV_OPERATOR_TOKEN:-atlas-operator-022}" ]; then
    echo "authentication tokens must not be empty" >&2
    exit 2
fi

mkdir -p "$RUNTIME_DIR"
mkdir -p "$(dirname "$DATABASE")"

if [ ! -f "$BASELINE" ]; then
    BASELINE="$RUNTIME_DIR/generated_baseline.sqlite3"
    python /app/generate_data.py --output "$BASELINE" --manifest "$RUNTIME_DIR/generated_manifest.json" >/dev/null
fi

TEMP_DATABASE="$DATABASE.initializing"
rm -f "$TEMP_DATABASE"
cp "$BASELINE" "$TEMP_DATABASE"
chmod 0600 "$TEMP_DATABASE"
mv -f "$TEMP_DATABASE" "$DATABASE"

export TASK_ENV_BIND="$BIND"
export TASK_ENV_PORT="$PORT"
export TASK_ENV_BASELINE="$BASELINE"
export TASK_ENV_DATABASE="$DATABASE"

exec python /app/app.py
