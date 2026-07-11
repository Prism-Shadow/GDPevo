#!/usr/bin/env python3
"""Evaluator for task_group_020 train_002."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
DEFAULT_PREDICTION = TASK_DIR / "output" / "answer.json"
TOTAL_WEIGHT = 17


def load_prediction(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return None, f"Prediction file not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "Top-level prediction must be a JSON object."
    return data, None


def issue_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    issues = data.get("issues", [])
    if not isinstance(issues, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue_id = item.get("issue_id")
        if isinstance(issue_id, str) and issue_id not in indexed:
            indexed[issue_id] = item
    return indexed


def cv(issue: dict[str, Any]) -> dict[str, Any]:
    value = issue.get("corrected_value", {})
    return value if isinstance(value, dict) else {}


def is_number(value: Any, expected: float, decimals: int = 2) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return round(float(value), decimals) == round(float(expected), decimals)
    except (TypeError, ValueError):
        return False


def is_int(value: Any, expected: int) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return int(value) == expected and float(value) == float(expected)
    except (TypeError, ValueError):
        return False


def is_bool(value: Any, expected: bool) -> bool:
    return isinstance(value, bool) and value is expected


def is_set(value: Any, expected: set[str]) -> bool:
    return isinstance(value, list) and set(value) == expected and len(value) == len(expected)


def base_fields(issue: dict[str, Any], severity: str, action: str) -> bool:
    return issue.get("severity") == severity and issue.get("recommended_action") == action


def financing_condition(issues: dict[str, dict[str, Any]]) -> bool:
    issue = issues.get("FINANCING_CONDITION")
    if not issue or not base_fields(issue, "CRITICAL", "DELETE"):
        return False
    value = cv(issue)
    return (
        is_bool(value.get("financing_condition_allowed"), False)
        and is_bool(value.get("lender_diligence_condition_allowed"), False)
        and value.get("approval_required") == "EXECUTIVE_COMMITTEE"
        and value.get("replacement") == "CLOSING_CERTAINTY_COVENANT"
    )


def reverse_termination_fee(issues: dict[str, dict[str, Any]]) -> bool:
    issue = issues.get("REVERSE_TERMINATION_FEE")
    if not issue or not base_fields(issue, "HIGH", "ADD_FALLBACK_ONLY"):
        return False
    value = cv(issue)
    return (
        is_bool(value.get("fallback_only"), True)
        and value.get("fee_base") == "HEADLINE_VALUE"
        and is_number(value.get("reverse_fee_percent"), 7.26)
        and is_int(value.get("reverse_fee_amount_usd"), 17133600)
        and is_bool(value.get("parent_guarantee_required"), True)
        and is_bool(value.get("financing_condition_must_still_be_deleted"), True)
    )


def escrow(issues: dict[str, dict[str, Any]]) -> bool:
    issue = issues.get("ESCROW")
    if not issue or not base_fields(issue, "HIGH", "REVISE"):
        return False
    value = cv(issue)
    return (
        is_number(value.get("escrow_percent"), 7.5)
        and is_int(value.get("escrow_amount_usd"), 17700000)
        and is_number(value.get("fallback_escrow_percent"), 10.0)
        and is_int(value.get("fallback_escrow_amount_usd"), 23600000)
        and is_int(value.get("release_months"), 12)
        and value.get("investment_benefit") == "FOR_SELLER"
        and is_bool(value.get("escrow_longer_than_survival_allowed"), False)
    )


def survival_cap_basket(issues: dict[str, dict[str, Any]]) -> bool:
    issue = issues.get("SURVIVAL_CAP_BASKET")
    if not issue or not base_fields(issue, "HIGH", "REVISE"):
        return False
    value = cv(issue)
    return (
        is_int(value.get("seller_rep_survival_months"), 12)
        and is_number(value.get("general_cap_percent"), 7.5)
        and is_int(value.get("general_cap_amount_usd"), 17700000)
        and is_number(value.get("basket_percent"), 1.0)
        and value.get("basket_type") == "DEDUCTIBLE"
        and is_bool(value.get("de_minimis_required"), True)
        and is_bool(value.get("tipping_allowed"), False)
    )


def assumed_liabilities_and_nwc(issues: dict[str, dict[str, Any]]) -> bool:
    issue = issues.get("ASSUMED_LIABILITIES_AND_NWC")
    if not issue or not base_fields(issue, "HIGH", "REVISE"):
        return False
    value = cv(issue)
    return (
        value.get("buyer_assumed_liability_covenant") == "SURVIVE_UNTIL_FULLY_PERFORMED"
        and is_bool(value.get("working_capital_reset_allowed"), False)
        and is_int(value.get("working_capital_target_usd"), 32100000)
        and is_int(value.get("working_capital_collar_usd"), 1200000)
    )


def restrictive_covenant(issues: dict[str, dict[str, Any]]) -> bool:
    issue = issues.get("RESTRICTIVE_COVENANT")
    if not issue or not base_fields(issue, "MEDIUM", "REVISE"):
        return False
    value = cv(issue)
    return (
        is_int(value.get("non_compete_years"), 3)
        and is_int(value.get("customer_non_solicit_years"), 4)
        and is_bool(value.get("worldwide_scope_allowed"), False)
        and is_bool(value.get("affiliate_wide_scope_allowed"), False)
        and value.get("business_scope") == "TRANSFERRED_BUSINESS_ONLY"
    )


def employee_tsa_ip_transition(issues: dict[str, dict[str, Any]]) -> bool:
    issue = issues.get("EMPLOYEE_TSA_IP_TRANSITION")
    if not issue or not base_fields(issue, "CRITICAL", "ADD"):
        return False
    value = cv(issue)
    return (
        is_bool(value.get("buyer_comparable_offer_required"), True)
        and value.get("warn_and_severance_liability") == "BUYER_FOR_TRANSFERRED_EMPLOYEES"
        and is_bool(value.get("tsa_required"), True)
        and is_set(
            value.get("tsa_services"),
            {"ERP", "IT_HELPDESK", "PAYROLL", "QUALITY_CERTIFICATIONS"},
        )
        and is_bool(value.get("ip_transition_license_required"), True)
        and is_bool(value.get("retained_ip_boundaries_required"), True)
        and is_int(value.get("trademark_phaseout_months"), 9)
    )


POINTS: list[tuple[str, int, str, Callable[[dict[str, dict[str, Any]]], bool]]] = [
    ("SP001", 3, "Financing condition issue", financing_condition),
    ("SP002", 2, "Reverse termination fee fallback math and recommendation", reverse_termination_fee),
    ("SP003", 2, "Escrow amount, release period, and investment benefit", escrow),
    ("SP004", 3, "Survival, cap, basket, and de minimis corrections", survival_cap_basket),
    ("SP005", 2, "Assumed-liability and working-capital reset protection", assumed_liabilities_and_nwc),
    ("SP006", 2, "Restrictive covenant narrowing", restrictive_covenant),
    ("SP007", 3, "Employee, TSA, and IP transition package", employee_tsa_ip_transition),
]


def zero_result(error: str) -> dict[str, Any]:
    return {
        "score": 0.0,
        "raw_score": 0,
        "max_raw_score": TOTAL_WEIGHT,
        "error": error,
        "point_results": [
            {
                "point_id": point_id,
                "description": description,
                "weight": weight,
                "passed": False,
                "raw_earned": 0,
                "normalized_earned": 0.0,
            }
            for point_id, weight, description, _ in POINTS
        ],
    }


def evaluate(path: Path) -> dict[str, Any]:
    data, error = load_prediction(path)
    if error is not None or data is None:
        return zero_result(error or "Unable to load prediction.")

    issues = issue_index(data)
    point_results = []
    raw_score = 0
    for point_id, weight, description, check in POINTS:
        passed = check(issues)
        earned = weight if passed else 0
        raw_score += earned
        point_results.append(
            {
                "point_id": point_id,
                "description": description,
                "weight": weight,
                "passed": passed,
                "raw_earned": earned,
                "normalized_earned": round(earned / TOTAL_WEIGHT, 10),
            }
        )

    return {
        "score": round(raw_score / TOTAL_WEIGHT, 10),
        "raw_score": raw_score,
        "max_raw_score": TOTAL_WEIGHT,
        "point_results": point_results,
    }


def main() -> int:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PREDICTION
    result = evaluate(prediction_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
