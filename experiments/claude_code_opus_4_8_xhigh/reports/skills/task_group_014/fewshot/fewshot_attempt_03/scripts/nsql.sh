#!/usr/bin/env bash
# nsql.sh — run ONE read-only SQL statement against the Northstar payer-operations
# environment and print the JSON response.
#
# Usage:
#   scripts/nsql.sh "SELECT * FROM cases WHERE case_id='CASE-...'"
#
# Base URL and bearer token are resolved in this order:
#   1. env vars  GDPEVO_ENV_BASE_URL  and  GDPEVO_SQL_TOKEN
#   2. parsed from an environment_access.md file (path in ENV_ACCESS_FILE, else
#      ./environment_access.md)
#
# Notes: the endpoint accepts only a single statement; writes/multi-statement are
# rejected. Results cap at 500 rows ("limited": true means the query was truncated).
set -euo pipefail

sql="${1:?usage: nsql.sh \"<single SELECT statement>\"}"
access_file="${ENV_ACCESS_FILE:-environment_access.md}"
base="${GDPEVO_ENV_BASE_URL:-}"
token="${GDPEVO_SQL_TOKEN:-}"

if [ -z "$base" ] && [ -f "$access_file" ]; then
  base="$(grep -oE 'GDPEVO_ENV_BASE_URL=[^[:space:]]+' "$access_file" | head -n1 | cut -d= -f2-)"
fi
if [ -z "$token" ] && [ -f "$access_file" ]; then
  token="$(grep -oE 'Bearer[[:space:]]+[^[:space:]]+' "$access_file" | head -n1 | awk '{print $2}')"
fi

if [ -z "$base" ]; then echo "error: base URL not found (set GDPEVO_ENV_BASE_URL or provide environment_access.md)" >&2; exit 2; fi
if [ -z "$token" ]; then echo "error: bearer token not found (set GDPEVO_SQL_TOKEN or provide environment_access.md)" >&2; exit 2; fi
base="${base%/}"

# JSON-encode the SQL string safely (handles quotes/newlines).
body="$(printf '%s' "$sql" | python3 -c 'import json,sys; print(json.dumps({"sql": sys.stdin.read()}))')"

curl -s -X POST "$base/sql/query" \
  -H "Authorization: Bearer $token" \
  -H "Content-Type: application/json" \
  --data "$body"
