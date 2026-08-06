#!/usr/bin/env bash
# Dump every Investigation Review Hub table for one matter.
#
# Usage:
#   pull_matter.sh <BASE_URL> <API_KEY> <MATTER_ID> [OUTDIR]
# Example:
#   pull_matter.sh http://task-env:9017 review-key-017 MTR-EXAMPLE-GJ ./hub_dump
#
# Reads the base URL / key from args; take them from the run's
# environment_access.md (GDPEVO_ENV_BASE_URL, X-API-Key) — do not hard-code.
# Requires: curl. Writes one JSON file per endpoint (or prints to stdout if no
# OUTDIR). Uses only the network API — never touches env source/db files.

set -euo pipefail

BASE="${1:?base url required}"; KEY="${2:?api key required}"; M="${3:?matter_id required}"
OUT="${4:-}"
BASE="${BASE%/}"

# endpoint:filename pairs
EPS=(
  "/api/matters:matters"
  "/api/subpoena-categories:subpoena_categories"
  "/api/productions:productions"
  "/api/custodian-sources:custodian_sources"
  "/api/documents/search:review_documents"
  "/api/privilege-log:privilege_log"
  "/api/qc-findings:qc_findings"
  "/api/retention-events:retention_events"
  "/api/remediation-actions:remediation_actions"
)

if [ -n "$OUT" ]; then mkdir -p "$OUT"; fi

fetch() { curl -s -m 30 -H "X-API-Key: $KEY" "$BASE$1?matter_id=$M"; }

echo "# Hub dump for matter=$M via $BASE" >&2
for pair in "${EPS[@]}"; do
  ep="${pair%%:*}"; name="${pair##*:}"
  echo "-- $ep" >&2
  if [ -n "$OUT" ]; then
    fetch "$ep" > "$OUT/$name.json"
  else
    echo "===== $name ($ep) ====="
    fetch "$ep"; echo
  fi
done

# review_documents is capped at 100 rows over the GET endpoint; pull the full set
# via SQL when you need completeness.
FULL_DOCS_SQL="{\"sql\":\"SELECT * FROM review_documents WHERE matter_id='$M'\"}"
if [ -n "$OUT" ]; then
  curl -s -m 30 -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
    -X POST "$BASE/api/query" -d "$FULL_DOCS_SQL" > "$OUT/review_documents_full.json" || true
  echo "# wrote files to $OUT/" >&2
else
  echo "===== review_documents_full (SQL, uncapped) =====";
  curl -s -m 30 -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
    -X POST "$BASE/api/query" -d "$FULL_DOCS_SQL"; echo
fi
