#!/usr/bin/env sh
# Authenticated helper for the Investigation Review Hub (read-only).
#
# Base URL resolution order:
#   1) $GDPEVO_ENV_BASE_URL  (as printed in environment_access.md)
#   2) $HUB_BASE_URL
#   3) first CLI arg when it looks like a URL
# API key: $HUB_API_KEY, else defaults to review-key-017 (the value in environment_access.md).
#
# Usage:
#   hub.sh get <path-with-leading-slash>          e.g.  hub.sh get "/api/custodian-sources?matter_id=MTR-X"
#   hub.sh sql "<SELECT …>"                        runs POST /api/query with {"sql": "…"}
#   hub.sh endpoints                               GET /  (service + endpoint list)
#
# Notes:
#   * SQL results are capped at 500 rows (response has "truncated":true when hit) —
#     use COUNT/SUM/GROUP BY for metrics, not raw-row dumps.
#   * Requires curl. Output is the raw JSON response on stdout.

set -eu

KEY="${HUB_API_KEY:-review-key-017}"

_base() {
  b="${GDPEVO_ENV_BASE_URL:-${HUB_BASE_URL:-}}"
  if [ -z "$b" ]; then
    case "${1:-}" in
      http://*|https://*) b="$1" ;;
      *) echo "hub.sh: no base URL (set GDPEVO_ENV_BASE_URL or HUB_BASE_URL)" >&2; exit 2 ;;
    esac
  fi
  # strip a single trailing slash
  printf '%s' "${b%/}"
}

_json_escape() {
  # minimal JSON string escaping for the SQL payload
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | awk 'BEGIN{ORS=""}{gsub(/\t/,"\\t"); print} END{}'
}

cmd="${1:-}"
case "$cmd" in
  get)
    path="${2:?usage: hub.sh get <path>}"
    base="$(_base "")"
    curl -sS -m 30 -H "X-API-Key: $KEY" "${base}${path}"
    echo
    ;;
  sql)
    sql="${2:?usage: hub.sh sql \"<SELECT …>\"}"
    base="$(_base "")"
    esc="$(_json_escape "$sql")"
    curl -sS -m 30 -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
      -X POST "${base}/api/query" -d "{\"sql\":\"${esc}\"}"
    echo
    ;;
  endpoints)
    base="$(_base "")"
    curl -sS -m 30 -H "X-API-Key: $KEY" "${base}/"
    echo
    ;;
  *)
    echo "usage: hub.sh {get <path>|sql <select>|endpoints}" >&2
    exit 2
    ;;
esac
