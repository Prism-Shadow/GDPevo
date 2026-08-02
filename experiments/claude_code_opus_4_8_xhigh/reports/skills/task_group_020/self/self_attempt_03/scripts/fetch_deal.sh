#!/usr/bin/env bash
# Bundle every workbench record for one deal into a single JSON document on stdout,
# including the playbook/policy that the deal record actually points to.
#
# Usage:  TASK_ENV_BASE_URL=http://host:port ./fetch_deal.sh PRJ_XXXX > deal.json
#
# The bundle also carries a `_decoys` array listing other deals that share this deal's
# project name, and `_stale_term_ids`, so both distractor traps are visible up front.

set -uo pipefail

DEAL_ID="${1:-}"
if [[ -z "$DEAL_ID" ]]; then
  echo "usage: $0 <DEAL_ID>" >&2
  exit 2
fi

BASE="${TASK_ENV_BASE_URL:-${GDPEVO_ENV_BASE_URL:-http://task-env:9020}}"
BASE="${BASE%/}"
TOKEN="${WORKBENCH_TOKEN:-deal-workbench-readonly}"

command -v jq >/dev/null || { echo "jq is required" >&2; exit 3; }

get() { curl -sS -m 20 "$BASE$1" 2>/dev/null; }

sql() {
  curl -sS -m 20 -X POST "$BASE/api/query" \
    -H 'Content-Type: application/json' \
    --data-binary "$(jq -n --arg t "$TOKEN" --arg s "$1" '{token:$t, sql:$s}')" 2>/dev/null
}

# Unwrap response envelopes. Content keys are not always the plural of the route segment
# (/terms -> draft_terms, /notes -> deal_notes), and some routes add a sibling "links" key,
# so prefer a known content key, then fall back to the sole key of a single-key object.
unwrap() {
  jq '
    def content:
      ["deal","draft_terms","deal_notes","documents","benchmarks","risk_estimates",
       "cap_table","consents","employees","material_contracts","regulatory",
       "diligence_findings","rules","thresholds"];
    if type == "object" then
      . as $o
      | (content | map(. as $c | select($o | has($c))) | first) as $k
      | if $k != null then $o[$k]
        elif ($o | keys | length) == 1 then ($o | to_entries[0].value)
        else $o end
    else . end
  ' 2>/dev/null
}

deal="$(get "/api/deals/$DEAL_ID" | unwrap)"
if [[ -z "$deal" ]] || ! jq -e 'type=="object" and has("deal_id")' <<<"$deal" >/dev/null 2>&1; then
  echo "error: could not fetch deal $DEAL_ID from $BASE" >&2
  exit 4
fi

playbook_id="$(jq -r '.playbook_id // empty' <<<"$deal")"
policy_id="$(jq -r '.policy_id   // empty' <<<"$deal")"
project_name="$(jq -r '.project_name // empty' <<<"$deal")"

rules='null'
[[ -n "$playbook_id" ]] && rules="$(get "/api/playbooks/$playbook_id/rules" | jq '.rules // .')"

thresholds='null'
[[ -n "$policy_id" ]] && thresholds="$(get "/api/policies/$policy_id/thresholds" | jq '.thresholds // .')"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for ep in terms documents benchmarks risk-estimates cap-table consents employees \
          material-contracts regulatory diligence-findings notes; do
  get "/api/deals/$DEAL_ID/$ep" | unwrap > "$tmp/${ep}.json" &
done
wait

# Other deals whose project name merely *resembles* this one — the near-name decoy trap.
# Matching is on the distinctive token ("Project Foo" -> "Foo"), so same-stem deals such as
# "Project Foo North" surface even though the names are not identical.
decoys='[]'
token="$(sed -E 's/^Project +//; s/ .*$//' <<<"$project_name")"
if [[ -n "$token" ]]; then
  esc="$(sed "s/'/''/g" <<<"$token")"
  decoys="$(sql "SELECT deal_id, project_name, target_name, client_side, playbook_id, policy_id FROM deals WHERE project_name LIKE '%${esc}%' AND deal_id <> '$DEAL_ID' ORDER BY deal_id" \
    | jq '[(.rows // [])[] | {deal_id:.[0], project_name:.[1], target_name:.[2], client_side:.[3], playbook_id:.[4], policy_id:.[5]}]' 2>/dev/null || echo '[]')"
fi

rd() { jq '.' "$tmp/$1.json" 2>/dev/null || echo 'null'; }

jq -n \
  --argjson deal              "$deal" \
  --argjson playbook_rules    "${rules:-null}" \
  --argjson policy_thresholds "${thresholds:-null}" \
  --argjson terms             "$(rd terms)" \
  --argjson documents         "$(rd documents)" \
  --argjson benchmarks        "$(rd benchmarks)" \
  --argjson risk_estimates    "$(rd risk-estimates)" \
  --argjson cap_table         "$(rd cap-table)" \
  --argjson consents          "$(rd consents)" \
  --argjson employees         "$(rd employees)" \
  --argjson material_contracts "$(rd material-contracts)" \
  --argjson regulatory        "$(rd regulatory)" \
  --argjson findings          "$(rd diligence-findings)" \
  --argjson notes             "$(rd notes)" \
  --argjson decoys            "${decoys:-[]}" \
  '{
     deal: $deal,
     binding_standard: {
       playbook_id: $deal.playbook_id,
       policy_id: $deal.policy_id,
       playbook_rules: $playbook_rules,
       policy_thresholds: $policy_thresholds
     },
     current_terms: [ ($terms // [])[] | select(.staleness_flag != "stale") ],
     documents: $documents, benchmarks: $benchmarks, risk_estimates: $risk_estimates,
     cap_table: $cap_table, consents: $consents, employees: $employees,
     material_contracts: $material_contracts, regulatory: $regulatory,
     diligence_findings: $findings, notes: $notes,
     _decoys: $decoys,
     _stale_term_ids: [ ($terms // [])[] | select(.staleness_flag == "stale") | .term_id ],
     _rollups: {
       headline_value: $deal.headline_value,
       upfront_cash: $deal.upfront_cash,
       employee_headcount: ([ ($employees // [])[].count ] | add // 0),
       pto_liability_total: ([ ($employees // [])[].pto_liability ] | add // 0),
       closing_consent_amount_at_risk:
         ([ ($consents // [])[] | select(.required_for_closing=="yes") | .amount_at_risk ] | add // 0),
       consent_required_contract_revenue:
         ([ ($material_contracts // [])[] | select(.consent_required=="yes") | .annual_revenue ] | add // 0),
       exposure_low:  ([ ($risk_estimates // [])[].exposure_low ]  | add // 0),
       exposure_high: ([ ($risk_estimates // [])[].exposure_high ] | add // 0)
     }
   }'
