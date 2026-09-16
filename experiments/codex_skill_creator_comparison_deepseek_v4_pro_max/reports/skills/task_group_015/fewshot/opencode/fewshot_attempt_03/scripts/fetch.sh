#!/usr/bin/env bash
# Fetch a single endpoint from the EHR quality-governance API.
# Usage: bash fetch.sh /api/patients/P-31014
#
# Reads TASK_ENV_BASE_URL from the environment. Set it before calling:
#   export TASK_ENV_BASE_URL="http://task-env:9015"
#
# Handles connection timeouts and retries once on transient failures.
# Outputs the raw JSON body to stdout.

set -euo pipefail

endpoint_path="${1:-}"

if [ -z "$endpoint_path" ]; then
  echo "usage: fetch.sh <endpoint-path>  (e.g. /api/patients/P-31014)" >&2
  exit 1
fi

BASE_URL="${TASK_ENV_BASE_URL:-}"
if [ -z "$BASE_URL" ]; then
  echo "fetch.sh: TASK_ENV_BASE_URL is not set" >&2
  exit 1
fi

# Strip trailing slash from base URL, ensure leading slash on path
BASE_URL="${BASE_URL%/}"
[[ "$endpoint_path" == /* ]] || endpoint_path="/$endpoint_path"

FULL_URL="${BASE_URL}${endpoint_path}"

# First attempt
HTTP_CODE=$(curl -s -w '%{http_code}' -o /tmp/fetch_response.json \
  --connect-timeout 10 --max-time 30 "$FULL_URL" 2>/dev/null || echo "000")

# Retry once on transient failures (5xx or connection errors)
if [ "$HTTP_CODE" = "000" ] || [ "${HTTP_CODE:0:1}" = "5" ]; then
  HTTP_CODE=$(curl -s -w '%{http_code}' -o /tmp/fetch_response.json \
    --connect-timeout 10 --max-time 30 "$FULL_URL" 2>/dev/null || echo "000")
fi

if [ "$HTTP_CODE" != "200" ]; then
  echo "fetch.sh: request to $endpoint_path returned HTTP $HTTP_CODE" >&2
  cat /tmp/fetch_response.json >&2
  exit 1
fi

cat /tmp/fetch_response.json
