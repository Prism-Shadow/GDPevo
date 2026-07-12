#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATED_DIR="${ENV_DIR}/generated"
DB_PATH="${GENERATED_DIR}/ops_analytics.sqlite"
MANIFEST_PATH="${GENERATED_DIR}/manifest.json"
HOST="${TASK_ENV_HOST:-0.0.0.0}"
PORT="${TASK_ENV_PORT:-8050}"
SERVE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --no-serve|--generate-only)
      SERVE=0
      shift
      ;;
    --serve)
      SERVE=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "${GENERATED_DIR}"
python3 "${ENV_DIR}/generate_data.py" \
  --db "${DB_PATH}" \
  --schema "${ENV_DIR}/schema.sql" \
  --manifest "${MANIFEST_PATH}"

if [[ -n "${TASK_ENV_BASE_URL:-}" ]]; then
  printf 'export TASK_ENV_BASE_URL=%q\n' "${TASK_ENV_BASE_URL}" > "${ENV_DIR}/task_env.sh"
else
  cat > "${ENV_DIR}/task_env.sh" <<'EOF'
# TASK_ENV_BASE_URL must be set to the externally reachable URL by the evaluation workspace.
EOF
fi

echo "Generated SQLite database: ${DB_PATH}"
echo "Wrote environment exports: ${ENV_DIR}/task_env.sh"
echo "API listen address: http://${HOST}:${PORT}"

if [[ "${SERVE}" == "1" ]]; then
  exec python3 "${ENV_DIR}/api_server.py" --db "${DB_PATH}" --host "${HOST}" --port "${PORT}"
fi
