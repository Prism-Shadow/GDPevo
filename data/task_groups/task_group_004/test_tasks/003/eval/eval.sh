#!/usr/bin/env bash
set -euo pipefail

TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREDICTION_PATH="${1:-"$TASK_DIR/output/answer.json"}"

python3 - "$PREDICTION_PATH" <<'PY'
import json
import math
import sys
from pathlib import Path

prediction_path = Path(sys.argv[1])

expected_actions = [
    {"customer_name": "Globex North Holdings LLC", "link_status": "linked", "account_id": "acct_globex_north", "overdue_balance": 19708.44, "primary_action": "collections_followup", "task_scope": "company_linked", "due_date": "2027-01-15"},
    {"customer_name": "Globex North Subsidiary LLC", "link_status": "unlinked", "account_id": None, "overdue_balance": 22322.33, "primary_action": "collections_followup", "task_scope": "standalone", "due_date": "2027-01-15"},
    {"customer_name": "North Star Finance Services", "link_status": "unlinked", "account_id": None, "overdue_balance": 18557.74, "primary_action": "collections_followup", "task_scope": "standalone", "due_date": "2027-01-15"},
    {"customer_name": "Northstar Finance Group Inc.", "link_status": "linked", "account_id": "acct_northstar_finance", "overdue_balance": 8688.06, "primary_action": "collections_followup", "task_scope": "company_linked", "due_date": "2027-01-15"},
    {"customer_name": "Polaris Health Network Inc.", "link_status": "linked", "account_id": "acct_polaris_health", "overdue_balance": 9104.24, "primary_action": "collections_followup", "task_scope": "company_linked", "due_date": "2027-01-15"},
    {"customer_name": "Riverbend Bank Foundation", "link_status": "unlinked", "account_id": None, "overdue_balance": 3590.27, "primary_action": "collections_followup", "task_scope": "standalone", "due_date": "2027-01-15"},
    {"customer_name": "Valence Payment Services Canada", "link_status": "unlinked", "account_id": None, "overdue_balance": 17157.87, "primary_action": "collections_followup", "task_scope": "standalone", "due_date": "2027-01-15"},
    {"customer_name": "Valence Payment Services LLC", "link_status": "linked", "account_id": "acct_valence", "overdue_balance": 6580.76, "primary_action": "collections_followup", "task_scope": "company_linked", "due_date": "2027-01-15"},
]

expected = {
    "operations_digest": {
        "region": "North America",
        "quarter": "2026-Q4",
        "overdue_client_count": 8,
        "overdue_total": 105709.71,
        "won_count": 2,
        "won_revenue": 252861.65,
        "lost_count": 0,
        "open_count": 9,
        "open_pipeline": 562286.74,
        "win_rate_pct": 100.0,
    },
    "leadership_flags": {
        "hr_headcount": 101,
        "unpaid_claims_amount": 26294.25,
        "event_orders": 251,
        "event_revenue": 179151.04,
        "dominant_pipeline_product_line": "Core Retention",
    },
    "policy_audit": {
        "receivable_trigger_basis": "late_bucket_only",
        "aging_balance_definition": "late_bucket_sum",
        "crm_match_basis": "exact_legal_name",
        "alias_handling": "do_not_link_aliases",
        "followup_scope_basis": "linked_when_exact_else_standalone",
        "pipeline_window_basis": "close_date_current_stage",
        "win_rate_denominator": "closed_won_lost_only",
        "open_pipeline_basis": "non_closed_stages_in_window",
    },
    "policy_codes": {
        "receivable_trigger_code": "RCP-7",
        "crm_match_code": "CM-5",
        "pipeline_window_code": "PW-6",
        "followup_scope_code": "FS-4",
    },
}

rubric = [
    ("regional_overdue_client_set", 1),
    ("link_status_and_account_ids", 2),
    ("overdue_balances_and_total", 1),
    ("receivable_actions_and_due_dates", 1),
    ("won_lost_counts_and_won_revenue", 1),
    ("open_pipeline_and_dominant_product", 1),
    ("hr_event_leadership_flags", 1),
    ("receivable_trigger_code", 3),
    ("crm_match_and_scope_codes", 3),
    ("pipeline_policy_code_set", 3),
]
total_weight = sum(weight for _, weight in rubric)

def as_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def money_equal(actual, expected_value):
    number = as_number(actual)
    return number is not None and math.isclose(round(number, 2), expected_value, abs_tol=0.001)

def pct_equal(actual, expected_value):
    number = as_number(actual)
    return number is not None and math.isclose(round(number, 1), expected_value, abs_tol=0.001)

try:
    prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(json.dumps({
        "score": 0,
        "earned_weight": 0,
        "total_weight": total_weight,
        "error": f"Could not read prediction JSON: {exc}",
    }, indent=2, sort_keys=True))
    sys.exit(0)

digest = prediction.get("operations_digest", {})
flags = prediction.get("leadership_flags", {})
policy = prediction.get("policy_audit", {})
policy_codes = prediction.get("policy_codes", {})
actions = prediction.get("receivable_actions", [])
if not isinstance(actions, list):
    actions = []

expected_by_name = {row["customer_name"]: row for row in expected_actions}
actual_by_name = {
    row.get("customer_name"): row
    for row in actions
    if isinstance(row, dict) and row.get("customer_name") is not None
}

checks = {}

checks["regional_overdue_client_set"] = (
    digest.get("region") == expected["operations_digest"]["region"]
    and digest.get("quarter") == expected["operations_digest"]["quarter"]
    and digest.get("overdue_client_count") == expected["operations_digest"]["overdue_client_count"]
    and set(actual_by_name) == set(expected_by_name)
)

checks["link_status_and_account_ids"] = all(
    actual_by_name.get(name, {}).get("link_status") == exp["link_status"]
    and actual_by_name.get(name, {}).get("account_id") == exp["account_id"]
    for name, exp in expected_by_name.items()
)

checks["overdue_balances_and_total"] = (
    money_equal(digest.get("overdue_total"), expected["operations_digest"]["overdue_total"])
    and all(
        money_equal(actual_by_name.get(name, {}).get("overdue_balance"), exp["overdue_balance"])
        for name, exp in expected_by_name.items()
    )
)

checks["receivable_actions_and_due_dates"] = all(
    actual_by_name.get(name, {}).get("primary_action") == exp["primary_action"]
    and actual_by_name.get(name, {}).get("task_scope") == exp["task_scope"]
    and actual_by_name.get(name, {}).get("due_date") == exp["due_date"]
    for name, exp in expected_by_name.items()
)

checks["won_lost_counts_and_won_revenue"] = (
    digest.get("won_count") == expected["operations_digest"]["won_count"]
    and money_equal(digest.get("won_revenue"), expected["operations_digest"]["won_revenue"])
    and digest.get("lost_count") == expected["operations_digest"]["lost_count"]
)

checks["open_pipeline_and_dominant_product"] = (
    digest.get("open_count") == expected["operations_digest"]["open_count"]
    and money_equal(digest.get("open_pipeline"), expected["operations_digest"]["open_pipeline"])
    and flags.get("dominant_pipeline_product_line") == expected["leadership_flags"]["dominant_pipeline_product_line"]
)

checks["hr_event_leadership_flags"] = (
    flags.get("hr_headcount") == expected["leadership_flags"]["hr_headcount"]
    and money_equal(flags.get("unpaid_claims_amount"), expected["leadership_flags"]["unpaid_claims_amount"])
    and flags.get("event_orders") == expected["leadership_flags"]["event_orders"]
    and money_equal(flags.get("event_revenue"), expected["leadership_flags"]["event_revenue"])
)

checks["receivable_and_match_policy_audit"] = (
    policy.get("receivable_trigger_basis") == expected["policy_audit"]["receivable_trigger_basis"]
    and policy.get("aging_balance_definition") == expected["policy_audit"]["aging_balance_definition"]
    and policy.get("crm_match_basis") == expected["policy_audit"]["crm_match_basis"]
    and policy.get("alias_handling") == expected["policy_audit"]["alias_handling"]
    and policy.get("followup_scope_basis") == expected["policy_audit"]["followup_scope_basis"]
)

checks["pipeline_policy_audit"] = (
    policy.get("pipeline_window_basis") == expected["policy_audit"]["pipeline_window_basis"]
    and policy.get("win_rate_denominator") == expected["policy_audit"]["win_rate_denominator"]
    and policy.get("open_pipeline_basis") == expected["policy_audit"]["open_pipeline_basis"]
)

checks["receivable_trigger_code"] = (
    policy_codes.get("receivable_trigger_code") == expected["policy_codes"]["receivable_trigger_code"]
)

checks["crm_match_and_scope_codes"] = (
    policy_codes.get("crm_match_code") == expected["policy_codes"]["crm_match_code"]
    and policy_codes.get("followup_scope_code") == expected["policy_codes"]["followup_scope_code"]
)

checks["pipeline_policy_code_set"] = (
    policy_codes.get("pipeline_window_code") == expected["policy_codes"]["pipeline_window_code"]
    and policy_codes == expected["policy_codes"]
)

earned_weight = sum(weight for key, weight in rubric if checks.get(key))
result = {
    "score": round(earned_weight / total_weight, 6),
    "earned_weight": earned_weight,
    "total_weight": total_weight,
    "checks": checks,
}
print(json.dumps(result, indent=2, sort_keys=True))
PY
