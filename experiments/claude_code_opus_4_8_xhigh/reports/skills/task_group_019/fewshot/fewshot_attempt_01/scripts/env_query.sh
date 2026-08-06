#!/usr/bin/env bash
# Query the licensing data service described in environment_access.md.
#
# Usage:
#   env_query.sh get "/api/policies"
#   env_query.sh sql "SELECT * FROM contractor_bonds WHERE application_id LIKE 'C-TR1-%'"
#
# Resolves the base URL and X-Task-Token from environment_access.md. Pass the file
# path as $ENV_ACCESS_FILE, else it looks in ./ and ../ (task root). Prints raw JSON;
# pipe to jq as needed.
set -euo pipefail

mode="${1:?usage: env_query.sh get|sql <path|query>}"
arg="${2:?missing path or query}"

find_access_file() {
  if [[ -n "${ENV_ACCESS_FILE:-}" && -f "${ENV_ACCESS_FILE}" ]]; then
    echo "${ENV_ACCESS_FILE}"; return
  fi
  for c in ./environment_access.md ../environment_access.md ../../environment_access.md; do
    [[ -f "$c" ]] && { echo "$c"; return; }
  done
  echo "environment_access.md not found (set ENV_ACCESS_FILE)" >&2; exit 1
}

ACCESS="$(find_access_file)"
BASE="$(grep -oE 'https?://[^[:space:]]+' "$ACCESS" | head -1)"
BASE="${BASE%/}"
# Token: the value after "X-Task-Token:" mentioned in the allowed-credentials section.
TOKEN="$(grep -oE 'X-Task-Token:[[:space:]]*[^[:space:]]+' "$ACCESS" | head -1 | sed -E 's/.*X-Task-Token:[[:space:]]*//')"

case "$mode" in
  get)
    path="${arg#/}"
    curl -sS -m 30 "${BASE}/${path}"
    ;;
  sql)
    # JSON-encode the query safely with jq, then POST.
    body="$(jq -nc --arg q "$arg" '{query:$q}')"
    curl -sS -m 30 -X POST "${BASE}/api/sql" \
      -H "X-Task-Token: ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$body"
    ;;
  *)
    echo "unknown mode: $mode (use get|sql)" >&2; exit 1
    ;;
esac
