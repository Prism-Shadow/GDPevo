#!/usr/bin/env bash
# Query the Court Operations Portal and pretty-print the JSON.
#
# Usage:
#   scripts/portal.sh <endpoint> [key=value ...]
#
# Examples (replace the placeholders with the target IDs from prompt.txt):
#   scripts/portal.sh cases case_number=<CASE_NUMBER>
#   scripts/portal.sh fee-schedules jurisdiction_code=<JURISDICTION_CODE>
#   scripts/portal.sh citations citation_number=<CITATION_NUMBER>
#   scripts/portal.sh payment-policies jurisdiction_code=<JURISDICTION_CODE>
#   scripts/portal.sh search q=<name-or-id>
#
# Base URL resolution order:
#   1. $GDPEVO_ENV_BASE_URL
#   2. the GDPEVO_ENV_BASE_URL=... line in ./environment_access.md (searched
#      upward from the current dir, then from this script's dir)
set -euo pipefail

find_base() {
  if [[ -n "${GDPEVO_ENV_BASE_URL:-}" ]]; then
    printf '%s' "$GDPEVO_ENV_BASE_URL"; return 0
  fi
  local dir
  for dir in "$PWD" "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; do
    while [[ -n "$dir" && "$dir" != "/" ]]; do
      if [[ -f "$dir/environment_access.md" ]]; then
        grep -m1 -oE 'GDPEVO_ENV_BASE_URL=[^[:space:]]+' "$dir/environment_access.md" \
          | cut -d= -f2- && return 0
      fi
      dir="$(dirname "$dir")"
    done
  done
  return 1
}

urlencode() {  # minimal: spaces and a few reserved chars
  local s="$1"
  s="${s// /%20}"; s="${s//&/%26}"; s="${s//#/%23}"; s="${s//+/%2B}"
  printf '%s' "$s"
}

if [[ $# -lt 1 ]]; then
  echo "usage: portal.sh <endpoint> [key=value ...]" >&2; exit 2
fi

base="$(find_base || true)"
if [[ -z "$base" ]]; then
  echo "error: could not resolve base URL (set GDPEVO_ENV_BASE_URL or run from the task dir)" >&2
  exit 1
fi
base="${base%/}"

endpoint="$1"; shift
query=""
for kv in "$@"; do
  key="${kv%%=*}"; val="$(urlencode "${kv#*=}")"
  query="${query:+$query&}${key}=${val}"
done

url="$base/api/$endpoint${query:+?$query}"
curl -s -m 20 "$url" | python3 -m json.tool
