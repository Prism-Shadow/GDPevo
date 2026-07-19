#!/usr/bin/env python3
"""Evaluator for train_005 May therapy margin queue."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable


EXPECTED_ROWS = {
    "SM-TR-005-MCD": {
        "payer_segment": "medicaid",
        "service_domain": "physical_therapy",
        "cpt_code": "97110",
        "total_cost": 26240.00,
        "margin": -2550.00,
        "revenue_to_cost_ratio": 0.9028,
        "below_threshold": True,
        "charge_sensitive": False,
        "recommended_action": "payer_contract_review",
    },
    "SM-TR-005-COM": {
        "payer_segment": "commercial",
        "service_domain": "physical_therapy",
        "cpt_code": "97530",
        "total_cost": 31700.00,
        "margin": 13570.00,
        "revenue_to_cost_ratio": 1.4281,
        "below_threshold": False,
        "charge_sensitive": True,
        "recommended_action": "monitor_charge_sensitive",
    },
    "SM-TR-005-WC": {
        "payer_segment": "workers_comp",
        "service_domain": "physical_therapy",
        "cpt_code": "97112",
        "total_cost": 13520.00,
        "margin": 12240.00,
        "revenue_to_cost_ratio": 1.9053,
        "below_threshold": False,
        "charge_sensitive": True,
        "recommended_action": "monitor_charge_sensitive",
    },
}

EXPECTED_ORDER = ["SM-TR-005-MCD", "SM-TR-005-COM", "SM-TR-005-WC"]
EXPECTED_BELOW_SEGMENTS = ["medicaid"]
EXPECTED_CHARGE_SEGMENTS = ["commercial", "workers_comp"]
EXPECTED_BASIS_AUDIT = {
    "source_precedence": "margin_threshold_then_charge_sensitivity",
    "precedence_record_order": ["sm-tr-005-mcd", "sm-tr-005-com", "sm-tr-005-wc"],
    "controlling_record_ids": ["sm-tr-005-mcd", "sm-tr-005-com", "sm-tr-005-wc"],
    "exception_record_ids": ["sm-tr-005-mcd"],
}


def norm_text(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def money_eq(value: Any, expected: float) -> bool:
    number = as_float(value)
    return number is not None and math.isclose(number, expected, abs_tol=0.01)


def ratio_eq(value: Any, expected: float) -> bool:
    number = as_float(value)
    return number is not None and math.isclose(number, expected, abs_tol=0.00005)


def bool_eq(value: Any, expected: bool) -> bool:
    return isinstance(value, bool) and value is expected


def list_norm(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    return [norm_text(item) for item in value]


def lower_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    return [str(item or "").strip().lower() for item in value]


def row_map(answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = answer.get("rows")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        month_id = str(row.get("month_id", "")).strip()
        if month_id:
            result[month_id] = row
    return result


def exact_row_ids(rows_by_id: dict[str, dict[str, Any]]) -> bool:
    return set(rows_by_id) == set(EXPECTED_ROWS)


def check_case_period_threshold(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    passed = (
        norm_text(answer.get("case_id")) == "queue_tr_005"
        and str(answer.get("period", "")).strip() == "2026-05"
        and ratio_eq(answer.get("threshold_revenue_to_cost_ratio"), 1.2)
    )
    return passed, {
        "case_id": answer.get("case_id"),
        "period": answer.get("period"),
        "threshold_revenue_to_cost_ratio": answer.get("threshold_revenue_to_cost_ratio"),
    }


def check_costs_and_margins(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    rows_by_id = row_map(answer)
    passed = exact_row_ids(rows_by_id)
    details: dict[str, Any] = {"row_ids": sorted(rows_by_id)}
    for month_id, expected in EXPECTED_ROWS.items():
        row = rows_by_id.get(month_id, {})
        row_ok = money_eq(row.get("total_cost"), expected["total_cost"]) and money_eq(
            row.get("margin"), expected["margin"]
        )
        details[month_id] = {
            "total_cost": row.get("total_cost"),
            "margin": row.get("margin"),
            "passed": row_ok,
        }
        passed = passed and row_ok
    return passed, details


def check_ratios(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    rows_by_id = row_map(answer)
    passed = exact_row_ids(rows_by_id)
    details: dict[str, Any] = {"row_ids": sorted(rows_by_id)}
    for month_id, expected in EXPECTED_ROWS.items():
        row = rows_by_id.get(month_id, {})
        ratio_ok = ratio_eq(row.get("revenue_to_cost_ratio"), expected["revenue_to_cost_ratio"])
        details[month_id] = {
            "revenue_to_cost_ratio": row.get("revenue_to_cost_ratio"),
            "passed": ratio_ok,
        }
        passed = passed and ratio_ok
    return passed, details


def check_below_threshold_and_top_issue(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    rows_by_id = row_map(answer)
    flags_ok = exact_row_ids(rows_by_id)
    flag_details: dict[str, Any] = {}
    for month_id, expected in EXPECTED_ROWS.items():
        row = rows_by_id.get(month_id, {})
        flag_ok = bool_eq(row.get("below_threshold"), expected["below_threshold"])
        flag_details[month_id] = {"below_threshold": row.get("below_threshold"), "passed": flag_ok}
        flags_ok = flags_ok and flag_ok
    segments = list_norm(answer.get("below_threshold_segments"))
    passed = (
        flags_ok and segments == EXPECTED_BELOW_SEGMENTS and norm_text(answer.get("top_issue")) == "medicaid_97110"
    )
    return passed, {
        "below_threshold_segments": answer.get("below_threshold_segments"),
        "top_issue": answer.get("top_issue"),
        "row_flags": flag_details,
    }


def check_charge_sensitive_segments(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    rows_by_id = row_map(answer)
    flags_ok = exact_row_ids(rows_by_id)
    flag_details: dict[str, Any] = {}
    for month_id, expected in EXPECTED_ROWS.items():
        row = rows_by_id.get(month_id, {})
        flag_ok = bool_eq(row.get("charge_sensitive"), expected["charge_sensitive"])
        flag_details[month_id] = {"charge_sensitive": row.get("charge_sensitive"), "passed": flag_ok}
        flags_ok = flags_ok and flag_ok
    segments = list_norm(answer.get("charge_sensitive_segments"))
    passed = flags_ok and segments == EXPECTED_CHARGE_SEGMENTS
    return passed, {
        "charge_sensitive_segments": answer.get("charge_sensitive_segments"),
        "row_flags": flag_details,
    }


def check_recommended_actions(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    rows_by_id = row_map(answer)
    passed = exact_row_ids(rows_by_id)
    details: dict[str, Any] = {"row_ids": sorted(rows_by_id)}
    for month_id, expected in EXPECTED_ROWS.items():
        row = rows_by_id.get(month_id, {})
        action_ok = norm_text(row.get("recommended_action")) == expected["recommended_action"]
        identity_ok = (
            norm_text(row.get("payer_segment")) == expected["payer_segment"]
            and norm_text(row.get("service_domain")) == expected["service_domain"]
            and str(row.get("cpt_code", "")).strip() == expected["cpt_code"]
        )
        row_ok = action_ok and identity_ok
        details[month_id] = {
            "payer_segment": row.get("payer_segment"),
            "service_domain": row.get("service_domain"),
            "cpt_code": row.get("cpt_code"),
            "recommended_action": row.get("recommended_action"),
            "passed": row_ok,
        }
        passed = passed and row_ok
    return passed, details


def check_gap_to_120pct(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    passed = money_eq(answer.get("gap_to_120pct"), 7798.00)
    return passed, {"gap_to_120pct": answer.get("gap_to_120pct")}


def check_basis_audit(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    audit = answer.get("basis_audit") if isinstance(answer, dict) else None
    actual = {
        "source_precedence": norm_text(audit.get("source_precedence")) if isinstance(audit, dict) else None,
        "precedence_record_order": lower_list(audit.get("precedence_record_order"))
        if isinstance(audit, dict)
        else None,
        "controlling_record_ids": lower_list(audit.get("controlling_record_ids")) if isinstance(audit, dict) else None,
        "exception_record_ids": lower_list(audit.get("exception_record_ids")) if isinstance(audit, dict) else None,
    }
    return actual == EXPECTED_BASIS_AUDIT, {"expected": EXPECTED_BASIS_AUDIT, "actual": actual}


Check = Callable[[dict[str, Any]], tuple[bool, dict[str, Any]]]

RUBRIC: list[tuple[str, int, Check]] = [
    ("Correct period, case ID, and revenue-to-cost threshold.", 1, check_case_period_threshold),
    ("Correct row-level total costs and margins.", 2, check_costs_and_margins),
    ("Correct revenue-to-cost ratios to four decimals.", 2, check_ratios),
    ("Correct below-threshold segment and top issue.", 3, check_below_threshold_and_top_issue),
    ("Correct charge-sensitive segment set.", 2, check_charge_sensitive_segments),
    ("Correct recommended action by payer segment.", 2, check_recommended_actions),
    ("Correct gap to 120 percent for the Medicaid row.", 1, check_gap_to_120pct),
    ("Correct business basis-audit source, controlling records, and exception records.", 1, check_basis_audit),
]


def evaluate(answer: Any) -> dict[str, Any]:
    total_weight = sum(weight for _, weight, _ in RUBRIC)
    results = []
    if not isinstance(answer, dict):
        for goal, weight, _ in RUBRIC:
            assigned = weight / total_weight
            results.append(
                {
                    "goal": goal,
                    "weight": weight,
                    "assigned_score": assigned,
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": "Answer must be a JSON object."},
                }
            )
        return {"score": 0.0, "points": results, "total_weight": total_weight}

    earned_weight = 0
    for goal, weight, check in RUBRIC:
        passed, details = check(answer)
        assigned = weight / total_weight
        earned = assigned if passed else 0.0
        if passed:
            earned_weight += weight
        results.append(
            {
                "goal": goal,
                "weight": weight,
                "assigned_score": round(assigned, 10),
                "passed": bool(passed),
                "earned_score": round(earned, 10),
                "details": details,
            }
        )
    return {
        "score": round(earned_weight / total_weight, 10),
        "points": results,
        "total_weight": total_weight,
    }


def main() -> None:
    answer_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    try:
        answer = json.loads(answer_path.read_text(encoding="utf-8"))
        result = evaluate(answer)
    except Exception as exc:
        total_weight = sum(weight for _, weight, _ in RUBRIC)
        result = {
            "score": 0.0,
            "points": [
                {
                    "goal": goal,
                    "weight": weight,
                    "assigned_score": round(weight / total_weight, 10),
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": str(exc)},
                }
                for goal, weight, _ in RUBRIC
            ],
            "total_weight": total_weight,
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
