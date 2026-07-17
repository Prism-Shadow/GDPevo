#!/bin/sh
set -eu

cd "$(dirname "$0")"
DB_PATH="${TASK_ENV_DB_PATH:-generated/observatory.sqlite}"

validate_runtime() {
    case "${TASK_ENV_PORT:-9023}" in
        ''|*[!0-9]*) echo "TASK_ENV_PORT must be an integer" >&2; exit 2 ;;
    esac
    if [ "${TASK_ENV_PORT:-9023}" -lt 1 ] || [ "${TASK_ENV_PORT:-9023}" -gt 65535 ]; then
        echo "TASK_ENV_PORT must be between 1 and 65535" >&2
        exit 2
    fi
    case "${TASK_ENV_BIND:-0.0.0.0}" in
        *[!A-Za-z0-9.:_-]*) echo "TASK_ENV_BIND contains unsupported characters" >&2; exit 2 ;;
    esac
}

case "${1:-}" in
    --reseed)
        shift
        exec python3 generate_data.py --output "$DB_PATH" "$@"
        ;;
    --check)
        shift
        exec python3 generate_data.py --check --output "$DB_PATH" "$@"
        ;;
    '')
        validate_runtime
        exec python3 server.py
        ;;
    *)
        echo "Usage: setup.sh [--reseed|--check]" >&2
        exit 2
        ;;
esac
