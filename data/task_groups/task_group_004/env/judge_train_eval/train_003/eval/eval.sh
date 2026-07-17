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

expected_followups = [
    {"customer_name": "Aurora Textiles Ltd.", "link_status": "linked", "account_id": "acct_aurora_textiles", "overdue_balance": 1758.82, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Globex North Holdings LLC", "link_status": "linked", "account_id": "acct_globex_north", "overdue_balance": 20929.75, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Globex North Subsidiary LLC", "link_status": "unlinked", "account_id": None, "overdue_balance": 15829.27, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Lumen Rail Systems Ltd.", "link_status": "linked", "account_id": "acct_lumen_rail", "overdue_balance": 12775.74, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "North Star Finance Services", "link_status": "unlinked", "account_id": None, "overdue_balance": 20013.87, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Northstar Finance Group Inc.", "link_status": "linked", "account_id": "acct_northstar_finance", "overdue_balance": 8498.32, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Polaris Health Network Inc.", "link_status": "linked", "account_id": "acct_polaris_health", "overdue_balance": 16375.85, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Quartz Insurance Claims Ltd.", "link_status": "unlinked", "account_id": None, "overdue_balance": 22236.07, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Riverbend Bank Foundation", "link_status": "unlinked", "account_id": None, "overdue_balance": 18590.54, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Southridge Mining Ltd.", "link_status": "linked", "account_id": "acct_southridge", "overdue_balance": 5443.46, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "TandemWorks Software Oy", "link_status": "linked", "account_id": "acct_tandemworks", "overdue_balance": 784.37, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Valence Payment Services Canada", "link_status": "unlinked", "account_id": None, "overdue_balance": 42217.66, "due_date": "2026-10-15", "primary_action": "collections_followup"},
    {"customer_name": "Valence Payment Services LLC", "link_status": "linked", "account_id": "acct_valence", "overdue_balance": 4858.69, "due_date": "2026-10-15", "primary_action": "collections_followup"},
]

expected = {
    "financial_summary": {
        "overdue_client_count": 13,
        "overdue_total": 190312.41,
        "linked_followup_count": 8,
        "unlinked_followup_count": 5,
    },
    "pipeline_summary": {
        "won_count": 6,
        "won_revenue": 193720.31,
        "lost_count": 3,
        "open_count": 25,
        "open_pipeline": 3043511.10,
        "win_rate_pct": 66.7,
        "top_open_product_line": "Data Cloud",
    },
    "ops_context": {
        "hr_headcount": 377,
        "unpaid_claims_total": 92850.39,
        "event_orders": 445,
        "event_revenue": 309724.17,
    },
    "policy_codes": {
        "receivable_trigger_code": "RCP-7",
        "crm_match_code": "CM-5",
        "pipeline_window_code": "PW-6",
        "followup_scope_code": "FS-4",
    },
}

rubric = [
    ("overdue_customer_set", 3),
    ("linkage_and_account_ids", 3),
    ("overdue_balances_and_totals", 2),
    ("followup_dates_and_actions", 2),
    ("won_lost_counts_and_won_revenue", 2),
    ("open_pipeline_summary", 2),
    ("win_rate", 1),
    ("hr_event_context", 2),
    ("policy_codes", 3),
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

financial = prediction.get("financial_summary", {})
pipeline = prediction.get("pipeline_summary", {})
ops = prediction.get("ops_context", {})
policy_codes = prediction.get("policy_codes", {})
followups = prediction.get("overdue_followups", [])
if not isinstance(followups, list):
    followups = []

expected_by_name = {row["customer_name"]: row for row in expected_followups}
actual_by_name = {
    row.get("customer_name"): row
    for row in followups
    if isinstance(row, dict) and row.get("customer_name") is not None
}

checks = {}

checks["overdue_customer_set"] = (
    set(actual_by_name) == set(expected_by_name)
    and financial.get("overdue_client_count") == expected["financial_summary"]["overdue_client_count"]
)

checks["linkage_and_account_ids"] = (
    financial.get("linked_followup_count") == expected["financial_summary"]["linked_followup_count"]
    and financial.get("unlinked_followup_count") == expected["financial_summary"]["unlinked_followup_count"]
    and all(
        actual_by_name.get(name, {}).get("link_status") == exp["link_status"]
        and actual_by_name.get(name, {}).get("account_id") == exp["account_id"]
        for name, exp in expected_by_name.items()
    )
)

checks["overdue_balances_and_totals"] = (
    money_equal(financial.get("overdue_total"), expected["financial_summary"]["overdue_total"])
    and all(
        money_equal(actual_by_name.get(name, {}).get("overdue_balance"), exp["overdue_balance"])
        for name, exp in expected_by_name.items()
    )
)

checks["followup_dates_and_actions"] = all(
    actual_by_name.get(name, {}).get("due_date") == exp["due_date"]
    and actual_by_name.get(name, {}).get("primary_action") == exp["primary_action"]
    for name, exp in expected_by_name.items()
)

checks["won_lost_counts_and_won_revenue"] = (
    pipeline.get("won_count") == expected["pipeline_summary"]["won_count"]
    and money_equal(pipeline.get("won_revenue"), expected["pipeline_summary"]["won_revenue"])
    and pipeline.get("lost_count") == expected["pipeline_summary"]["lost_count"]
)

checks["open_pipeline_summary"] = (
    pipeline.get("open_count") == expected["pipeline_summary"]["open_count"]
    and money_equal(pipeline.get("open_pipeline"), expected["pipeline_summary"]["open_pipeline"])
    and pipeline.get("top_open_product_line") == expected["pipeline_summary"]["top_open_product_line"]
)

checks["win_rate"] = pct_equal(pipeline.get("win_rate_pct"), expected["pipeline_summary"]["win_rate_pct"])

checks["hr_event_context"] = (
    ops.get("hr_headcount") == expected["ops_context"]["hr_headcount"]
    and money_equal(ops.get("unpaid_claims_total"), expected["ops_context"]["unpaid_claims_total"])
    and ops.get("event_orders") == expected["ops_context"]["event_orders"]
    and money_equal(ops.get("event_revenue"), expected["ops_context"]["event_revenue"])
)

checks["policy_codes"] = policy_codes == expected["policy_codes"]

earned_weight = sum(weight for key, weight in rubric if checks.get(key))
result = {
    "score": round(earned_weight / total_weight, 6),
    "earned_weight": earned_weight,
    "total_weight": total_weight,
    "checks": checks,
}
print(json.dumps(result, indent=2, sort_keys=True))
PY
