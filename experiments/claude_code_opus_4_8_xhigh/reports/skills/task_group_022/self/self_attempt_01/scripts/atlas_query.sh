#!/usr/bin/env bash
# Read-only Atlas SQL helper.
# Usage: atlas_query.sh "SELECT ..."   (one statement, no trailing semicolon)
#
# Reads the base URL and bearer token from environment_access.md so no
# credentials are hardcoded. Override by exporting ATLAS_BASE_URL / ATLAS_TOKEN.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 \"SELECT ...\"" >&2
  exit 2
fi
SQL="$1"

ENV_FILE="${ATLAS_ENV_FILE:-environment_access.md}"
BASE="${ATLAS_BASE_URL:-}"
TOKEN="${ATLAS_TOKEN:-}"

if [[ -z "$BASE" || -z "$TOKEN" ]] && [[ -f "$ENV_FILE" ]]; then
  # "Base URL: http://host:port/"  and  "Authorization: Bearer <token>"
  [[ -z "$BASE"  ]] && BASE="$(grep -iE '^Base URL:' "$ENV_FILE" | head -1 | sed -E 's/^[^:]*:[[:space:]]*//; s#/*$##')"
  [[ -z "$TOKEN" ]] && TOKEN="$(grep -iE '^Authorization:[[:space:]]*Bearer' "$ENV_FILE" | head -1 | sed -E 's/^[^:]*:[[:space:]]*Bearer[[:space:]]*//')"
fi

if [[ -z "$BASE" || -z "$TOKEN" ]]; then
  echo "error: could not resolve base URL / token (set ATLAS_BASE_URL and ATLAS_TOKEN, or provide $ENV_FILE)" >&2
  exit 3
fi

BODY="$(printf '%s' "$SQL" | python3 -c 'import json,sys; print(json.dumps({"sql": sys.stdin.read()}))')"

curl -s -m 60 \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$BODY" \
  "${BASE}/api/sql"
echo
