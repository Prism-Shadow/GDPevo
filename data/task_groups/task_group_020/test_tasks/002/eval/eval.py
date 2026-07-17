#!/usr/bin/env python3
"""Evaluator for task_group_020 test_002."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
DEFAULT_PREDICTION = TASK_DIR / "output" / "answer.json"
TOTAL_WEIGHT = 9


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


def corrected(issue: dict[str, Any]) -> dict[str, Any]:
    value = issue.get("corrected_terms", {})
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


def set_match(value: Any, expected: set[str]) -> bool:
    return isinstance(value, list) and set(value) == expected and len(value) == len(expected)


def base_fields(
    issue: dict[str, Any],
    severity: str,
    action: str,
    owners: set[str],
) -> bool:
    return (
        issue.get("severity") == severity
        and issue.get("recommended_action") == action
        and set_match(issue.get("approval_owners"), owners)
    )


def financing_fee(issues: dict[str, dict[str, Any]], data: dict[str, Any]) -> bool:
    issue = issues.get("FINANCING_FEE")
    if not issue or not base_fields(issue, "CRITICAL", "DELETE_AND_ADD_FALLBACK_FEE", {"EXECUTIVE_COMMITTEE"}):
        return False
    value = corrected(issue)
    return (
        is_bool(value.get("financing_condition_allowed"), False)
        and is_bool(value.get("reverse_fee_fallback_only"), True)
        and value.get("fee_base") == "HEADLINE_VALUE"
        and is_number(value.get("reverse_fee_percent"), 4.70)
        and is_int(value.get("reverse_fee_amount_usd"), 13442000)
        and is_bool(value.get("parent_guarantee_required"), True)
        and is_bool(value.get("financing_condition_must_still_be_deleted"), True)
    )


def escrow_terms(issues: dict[str, dict[str, Any]], data: dict[str, Any]) -> bool:
    issue = issues.get("ESCROW_TERMS")
    if not issue or not base_fields(issue, "HIGH", "REDUCE_OR_ESCALATE", {"SELLER_STEERING_COMMITTEE"}):
        return False
    value = corrected(issue)
    return (
        is_number(value.get("draft_escrow_percent"), 13.0)
        and is_int(value.get("draft_escrow_amount_usd"), 37180000)
        and is_number(value.get("target_escrow_percent"), 7.5)
        and is_int(value.get("target_escrow_amount_usd"), 21450000)
        and is_number(value.get("fallback_escrow_percent"), 10.0)
        and is_int(value.get("fallback_escrow_amount_usd"), 28600000)
        and is_int(value.get("draft_release_months"), 24)
        and is_int(value.get("target_release_months"), 12)
        and is_bool(value.get("escrow_above_fallback_requires_escalation"), True)
        and is_bool(value.get("escrow_longer_than_survival_allowed"), False)
    )


def survival_cap_basket(issues: dict[str, dict[str, Any]], data: dict[str, Any]) -> bool:
    issue = issues.get("SURVIVAL_CAP_BASKET_DE_MINIMIS")
    owners = {"DEAL_LEAD", "SELLER_STEERING_COMMITTEE"}
    if not issue or not base_fields(issue, "HIGH", "REVISE_AND_ESCALATE", owners):
        return False
    value = corrected(issue)
    return (
        is_int(value.get("draft_seller_rep_survival_months"), 24)
        and is_int(value.get("target_seller_rep_survival_months"), 12)
        and is_number(value.get("draft_general_cap_percent"), 20.0)
        and is_int(value.get("draft_general_cap_amount_usd"), 57200000)
        and is_number(value.get("target_general_cap_percent"), 7.5)
        and is_int(value.get("target_general_cap_amount_usd"), 21450000)
        and is_number(value.get("fallback_general_cap_percent"), 10.0)
        and is_int(value.get("fallback_general_cap_amount_usd"), 28600000)
        and is_number(value.get("basket_percent"), 1.0)
        and is_int(value.get("basket_amount_usd"), 2860000)
        and value.get("basket_type") == "DEDUCTIBLE"
        and is_bool(value.get("de_minimis_required"), True)
        and is_bool(value.get("tipping_allowed"), False)
    )


def employee_tsa_warn(issues: dict[str, dict[str, Any]], data: dict[str, Any]) -> bool:
    issue = issues.get("EMPLOYEE_TSA_WARN")
    owners = {"HR_COMMITTEE", "OPERATIONS_COMMITTEE"}
    if not issue or not base_fields(issue, "CRITICAL", "ADD_AND_ESCALATE", owners):
        return False
    value = corrected(issue)
    return (
        is_bool(value.get("buyer_comparable_offer_required"), True)
        and value.get("warn_liability") == "BUYER_FOR_TRANSFERRED_EMPLOYEES"
        and is_bool(value.get("seller_warn_retention_allowed"), False)
        and is_bool(value.get("tsa_required"), True)
        and value.get("tsa_status_required") == "DETAILED_EXHIBIT"
        and set_match(
            value.get("tsa_service_codes"),
            {"CHARGEBACK_SUPPORT", "COMPLIANCE_REPORTING", "KYC_OPERATIONS", "PROCESSOR_MIGRATION"},
        )
    )


def mae_carveouts(issues: dict[str, dict[str, Any]], data: dict[str, Any]) -> bool:
    issue = issues.get("MAE_CARVE_OUTS")
    if not issue or not base_fields(issue, "HIGH", "NARROW_AND_ESCALATE", {"SELLER_STEERING_COMMITTEE"}):
        return False
    value = corrected(issue)
    return (
        is_bool(value.get("unqualified_bank_sponsor_loss_trigger_allowed"), False)
        and is_bool(value.get("materiality_qualifier_required"), True)
        and is_bool(value.get("buyer_control_exception_required"), True)
        and is_bool(value.get("standard_market_carveouts_required"), True)
        and value.get("mae_position") == "MATERIALITY_AND_BUYER_CONTROL_EXCEPTIONS"
    )


def ip_transition(issues: dict[str, dict[str, Any]], data: dict[str, Any]) -> bool:
    issue = issues.get("IP_TRANSITION")
    if not issue or not base_fields(issue, "HIGH", "NARROW_AND_ESCALATE", {"IP_COUNSEL"}):
        return False
    value = corrected(issue)
    return (
        is_bool(value.get("perpetual_mark_use_allowed"), False)
        and is_bool(value.get("broad_source_repository_access_allowed"), False)
        and is_bool(value.get("transition_license_required"), True)
        and is_bool(value.get("retained_ip_boundaries_required"), True)
        and is_int(value.get("trademark_phaseout_months"), 9)
        and value.get("source_repository_access_scope") == "LIMITED_TRANSITION_ACCESS"
    )


def issue_ranking(issues: dict[str, dict[str, Any]], data: dict[str, Any]) -> bool:
    expected_order = [
        "FINANCING_FEE",
        "EMPLOYEE_TSA_WARN",
        "SURVIVAL_CAP_BASKET_DE_MINIMIS",
        "ESCROW_TERMS",
        "IP_TRANSITION",
        "MAE_CARVE_OUTS",
    ]
    summary = data.get("summary", {})
    if not isinstance(summary, dict):
        return False
    ranks_match = all(
        issues.get(issue_id, {}).get("rank") == index for index, issue_id in enumerate(expected_order, start=1)
    )
    return (
        summary.get("material_issue_count") == 6
        and summary.get("critical_issue_count") == 2
        and summary.get("highest_priority_issue_id") == "FINANCING_FEE"
        and summary.get("issue_priority_order") == expected_order
        and is_bool(summary.get("committee_escalation_required"), True)
        and set_match(
            summary.get("committee_escalation_owners"),
            {
                "EXECUTIVE_COMMITTEE",
                "HR_COMMITTEE",
                "IP_COUNSEL",
                "OPERATIONS_COMMITTEE",
                "SELLER_STEERING_COMMITTEE",
            },
        )
        and ranks_match
    )


POINTS: list[tuple[str, int, str, Callable[[dict[str, dict[str, Any]], dict[str, Any]], bool]]] = [
    ("SP001", 1, "Financing condition and reverse-fee fallback", financing_fee),
    ("SP002", 1, "Escrow amount, fallback, release period, and escalation", escrow_terms),
    ("SP003", 1, "Survival, cap, basket, and de minimis corrections", survival_cap_basket),
    ("SP004", 1, "Employee transfer, TSA, and WARN risk allocation", employee_tsa_warn),
    ("SP005", 3, "MAE sponsor-loss carve-out correction", mae_carveouts),
    ("SP006", 1, "IP transition license and access limits", ip_transition),
    ("SP007", 1, "Issue ranking and summary", issue_ranking),
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
        passed = check(issues, data)
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
