#!/usr/bin/env bash
# pull_matter.sh — dump every Investigation Review Hub table for one matter and
# pre-flag the likely MATERIAL anchor records (non-noise remediation targets +
# descriptive-slug records) so you can separate signal from distractors quickly.
#
# Usage:
#   BASE_URL and API_KEY are read from env vars, or from environment_access.md if
#   present, or fall back to the values passed as flags.
#
#   ./pull_matter.sh -m MTR-EXAMPLE-GJ [-b http://host:port] [-k api-key] [-e path/to/environment_access.md]
#
# Requires: curl, jq. This script is read-only (GET + SELECT only).
set -euo pipefail

MATTER=""
BASE="${GDPEVO_ENV_BASE_URL:-}"
KEY="${GDPEVO_API_KEY:-}"
ENVFILE=""

while getopts "m:b:k:e:h" opt; do
  case "$opt" in
    m) MATTER="$OPTARG" ;;
    b) BASE="$OPTARG" ;;
    k) KEY="$OPTARG" ;;
    e) ENVFILE="$OPTARG" ;;
    h) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown flag" >&2; exit 2 ;;
  esac
done

# Try to discover env file if base/key not supplied.
if [[ -z "$ENVFILE" ]]; then
  for c in environment_access.md ../environment_access.md ../../environment_access.md /work/environment_access.md; do
    [[ -f "$c" ]] && ENVFILE="$c" && break
  done
fi
if [[ -n "$ENVFILE" && -f "$ENVFILE" ]]; then
  [[ -z "$BASE" ]] && BASE="$(grep -iE 'BASE_URL' "$ENVFILE" | head -1 | sed -E 's/.*=[[:space:]]*//; s/[[:space:]]*$//')" || true
  [[ -z "$KEY"  ]] && KEY="$(grep -iE 'X-API-Key' "$ENVFILE" | head -1 | sed -E 's/.*X-API-Key:[[:space:]]*//; s/[[:space:]]*$//')" || true
fi

BASE="${BASE%/}"
if [[ -z "$MATTER" || -z "$BASE" || -z "$KEY" ]]; then
  echo "ERROR: need -m <matter_id>, a base URL, and an API key (env vars, env file, or flags)." >&2
  echo "  BASE='$BASE' KEY set=$([[ -n "$KEY" ]] && echo yes || echo no) MATTER='$MATTER'" >&2
  exit 2
fi

g()  { curl -s -m 30 -H "X-API-Key: $KEY" "$BASE$1"; }
sql() { curl -s -m 30 -X POST -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
          -d "{\"sql\":\"$1\",\"params\":[\"$MATTER\"]}" "$BASE/api/query"; }

echo "############ matter: $MATTER  @ $BASE ############"

echo; echo "===== matter metadata (note hold_date) ====="
g "/api/matters?matter_id=$MATTER" | jq -c '.rows[] | {matter_id,agency,investigation_type,hold_date,status}'

echo; echo "===== subpoena / request categories ====="
g "/api/subpoena-categories?matter_id=$MATTER" | jq -c '.rows[] | {category_code,title}'

echo; echo ">>> MATERIAL ANCHORS: non-noise remediation targets (start here) <<<"
sql "SELECT action_id,action_type,priority,severity,owner,target_ref,due_days FROM remediation_actions WHERE matter_id = ? AND action_id NOT LIKE '%NOISE%' ORDER BY priority, action_id" \
  | jq -c '.rows[]?'

echo; echo "--- (for reference) NOISE remediation rows, ignore ---"
sql "SELECT action_id,target_ref,description FROM remediation_actions WHERE matter_id = ? AND action_id LIKE '%NOISE%'" \
  | jq -c '.rows[]?'

echo; echo "===== retention_events (all — classify by status & event_date vs hold_date) ====="
g "/api/retention-events?matter_id=$MATTER" | jq -c '.rows[] | {event_id,status,record_type,event_date,hold_date,retention_period_months,volume_count,volume_unit,affected_categories,notes}'

echo; echo "===== custodian_sources (all — watch tags & post_hold) ====="
g "/api/custodian-sources?matter_id=$MATTER" | jq -c '.rows[] | {source_id,source_type,status,post_hold,category_impacts,issue_tags,notes}'

echo; echo "===== privilege_entries (all — incomplete_log / third_party / over_designated) ====="
g "/api/privilege-log?matter_id=$MATTER" | jq -c '.rows[] | {entry_id,category_code,issue_type,doc_count,withheld_count,logged_count,third_party,notes}'

echo; echo "===== qc_findings (all — miscoded_* are material) ====="
g "/api/qc-findings?matter_id=$MATTER" | jq -c '.rows[] | {finding_id,issue_type,doc_count,affected_category,source_ref,severity,notes}'

echo; echo "===== review_documents flagged with miscoded_nonresponsive (material responsiveness miscodes) ====="
g "/api/documents/search?matter_id=$MATTER" | jq -c '.rows[] | select((.issue_tags // []) | index("miscoded_nonresponsive")) | {doc_id,category_code,responsiveness,privilege_status,produced_status,issue_tags,summary}'

echo; echo "===== production_stats (zero-claim contradictions / large responsive-vs-produced gaps) ====="
g "/api/productions?matter_id=$MATTER" | jq -c '.rows[] | {batch_id,category_code,status,produced_count,responsive_count,zero_claim_reason,notes}'

echo; echo "NOTE: anchors above are candidates. Confirm each with the slug-id + concrete-note test"
echo "in reference/materiality_and_mapping.md before including it. Discard sequential-id + hedge-note rows."
