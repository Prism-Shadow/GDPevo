#!/usr/bin/env python3
"""Exact-match evaluator for task_group_018 test_002."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"

SCORING_POINTS = [
    {
        "id": "SP001",
        "weight": 2,
        "goal": "Correct target citations, row order, account references, defendant names, county, and batch id.",
        "kind": "ordered_identity",
    },
    {
        "id": "SP002",
        "weight": 3,
        "goal": "Correct source-resolution decisions, final plea/disposition posture, order dates, assessment statuses, and decision flags.",
        "kind": "source_posture",
    },
    {
        "id": "SP003",
        "weight": 3,
        "goal": "Correct violation code, violation source, and speed tier decisions, including amended and no-assessment rows.",
        "kind": "entry_fields",
        "fields": ["violation_code_for_assessment", "violation_source", "speed_tier"],
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct effective fee schedule buckets, assessed components, schedule effective starts, and per-entry assessed totals.",
        "kind": "components_and_totals",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct excluded candidate fee codes and unsupported-policy-code aggregate.",
        "kind": "excluded_codes",
    },
    {
        "id": "SP006",
        "weight": 3,
        "goal": "Correct payment-plan action, defect code, monthly amount, first due date, and first-due basis.",
        "kind": "plan_start",
    },
    {
        "id": "SP007",
        "weight": 2,
        "goal": "Correct installment counts, final payment amounts, total payment counts, and final due dates.",
        "kind": "installments",
    },
    {
        "id": "SP008",
        "weight": 2,
        "goal": "Correct monetary batch totals across prior/current schedules, fee categories, and entered plan principal.",
        "kind": "batch_money",
    },
    {
        "id": "SP009",
        "weight": 2,
        "goal": "Correct operational batch totals for assessment counts, exceptions, exclusions, plan defects, fee-schedule buckets, and post-disposition starts.",
        "kind": "batch_operational",
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def money(value: Any) -> str | None:
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, ValueError):
        return None


def entries(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    value = payload.get("entries")
    if not isinstance(value, list):
        return None
    if not all(isinstance(item, dict) for item in value):
        return None
    return value


def entry_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]] | None:
    rows = entries(payload)
    if rows is None:
        return None
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        citation_number = row.get("citation_number")
        if not isinstance(citation_number, str) or citation_number in mapped:
            return None
        mapped[citation_number] = row
    return mapped


def sorted_strings(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return sorted(value)


def normalize_components(value: Any) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        fee_code = item.get("fee_code")
        amount = money(item.get("amount"))
        schedule_effective_start = item.get("schedule_effective_start")
        if not isinstance(fee_code, str) or amount is None or not isinstance(schedule_effective_start, str):
            return None
        normalized.append(
            {
                "fee_code": fee_code,
                "amount": amount,
                "schedule_effective_start": schedule_effective_start,
            }
        )
    return normalized


def payment_plan(row: dict[str, Any]) -> dict[str, Any] | None:
    value = row.get("payment_plan")
    if not isinstance(value, dict):
        return None
    return value


def compare_ordered_identity(prediction: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    pred_rows = entries(prediction)
    exp_rows = entries(expected)
    if pred_rows is None:
        return False, "prediction.entries is not a list of objects"
    if exp_rows is None:
        return False, "answer entries are invalid"
    if prediction.get("batch_id") != expected.get("batch_id"):
        return False, "batch_id mismatch"
    if prediction.get("county") != expected.get("county"):
        return False, "county mismatch"
    if len(pred_rows) != len(exp_rows):
        return False, f"expected {len(exp_rows)} entries, got {len(pred_rows)}"
    fields = ("citation_number", "account_reference", "defendant_name")
    for idx, (pred_row, exp_row) in enumerate(zip(pred_rows, exp_rows)):
        for field in fields:
            if pred_row.get(field) != exp_row.get(field):
                return False, f"entry {idx} field {field} mismatch"
    return True, "matched"


def compare_entry_fields(
    prediction: dict[str, Any], expected: dict[str, Any], fields: tuple[str, ...] | list[str]
) -> tuple[bool, str]:
    pred_map = entry_map(prediction)
    exp_map = entry_map(expected)
    if pred_map is None:
        return False, "prediction.entries cannot be mapped by unique citation_number"
    if exp_map is None:
        return False, "answer entries are invalid"
    if set(pred_map) != set(exp_map):
        missing = sorted(set(exp_map) - set(pred_map))
        extra = sorted(set(pred_map) - set(exp_map))
        return False, f"citation set mismatch; missing={missing}; extra={extra}"
    for citation_number in sorted(exp_map):
        for field in fields:
            if pred_map[citation_number].get(field) != exp_map[citation_number].get(field):
                return False, f"{citation_number} field {field} mismatch"
    return True, "matched"


def compare_source_posture(prediction: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    pred_map = entry_map(prediction)
    exp_map = entry_map(expected)
    if pred_map is None:
        return False, "prediction.entries cannot be mapped by unique citation_number"
    if exp_map is None:
        return False, "answer entries are invalid"
    if set(pred_map) != set(exp_map):
        return False, "citation set mismatch"
    fields = (
        "source_resolution",
        "final_plea",
        "final_disposition",
        "assessment_order_date",
        "assessment_status",
    )
    for citation_number in sorted(exp_map):
        for field in fields:
            if pred_map[citation_number].get(field) != exp_map[citation_number].get(field):
                return False, f"{citation_number} field {field} mismatch"
        if sorted_strings(pred_map[citation_number].get("decision_flags")) != sorted_strings(
            exp_map[citation_number].get("decision_flags")
        ):
            return False, f"{citation_number} decision_flags mismatch"
    return True, "matched"


def compare_components_and_totals(prediction: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    pred_map = entry_map(prediction)
    exp_map = entry_map(expected)
    if pred_map is None:
        return False, "prediction.entries cannot be mapped by unique citation_number"
    if exp_map is None:
        return False, "answer entries are invalid"
    if set(pred_map) != set(exp_map):
        return False, "citation set mismatch"
    for citation_number in sorted(exp_map):
        if pred_map[citation_number].get("fee_schedule_bucket") != exp_map[citation_number].get("fee_schedule_bucket"):
            return False, f"{citation_number} fee_schedule_bucket mismatch"
        if normalize_components(pred_map[citation_number].get("assessed_components")) != normalize_components(
            exp_map[citation_number].get("assessed_components")
        ):
            return False, f"{citation_number} assessed_components mismatch"
        if money(pred_map[citation_number].get("assessed_total")) != money(
            exp_map[citation_number].get("assessed_total")
        ):
            return False, f"{citation_number} assessed_total mismatch"
    return True, "matched"


def compare_excluded_codes(prediction: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    pred_map = entry_map(prediction)
    exp_map = entry_map(expected)
    if pred_map is None:
        return False, "prediction.entries cannot be mapped by unique citation_number"
    if exp_map is None:
        return False, "answer entries are invalid"
    if set(pred_map) != set(exp_map):
        return False, "citation set mismatch"
    for citation_number in sorted(exp_map):
        if sorted_strings(pred_map[citation_number].get("excluded_candidate_fee_codes")) != sorted_strings(
            exp_map[citation_number].get("excluded_candidate_fee_codes")
        ):
            return False, f"{citation_number} excluded_candidate_fee_codes mismatch"
    pred_totals = prediction.get("batch_totals")
    exp_totals = expected.get("batch_totals")
    if not isinstance(pred_totals, dict) or not isinstance(exp_totals, dict):
        return False, "batch_totals is not an object"
    if pred_totals.get("unsupported_policy_code_count") != exp_totals.get("unsupported_policy_code_count"):
        return False, "unsupported_policy_code_count mismatch"
    return True, "matched"


def compare_plan_start(prediction: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    pred_map = entry_map(prediction)
    exp_map = entry_map(expected)
    if pred_map is None:
        return False, "prediction.entries cannot be mapped by unique citation_number"
    if exp_map is None:
        return False, "answer entries are invalid"
    if set(pred_map) != set(exp_map):
        return False, "citation set mismatch"
    fields = ("plan_action", "plan_defect_code", "first_due_date", "first_due_basis")
    for citation_number in sorted(exp_map):
        pred_plan = payment_plan(pred_map[citation_number])
        exp_plan = payment_plan(exp_map[citation_number])
        if pred_plan is None or exp_plan is None:
            return False, f"{citation_number} payment_plan is missing"
        for field in fields:
            if pred_plan.get(field) != exp_plan.get(field):
                return False, f"{citation_number} payment_plan.{field} mismatch"
        if money(pred_plan.get("monthly_amount")) != money(exp_plan.get("monthly_amount")):
            return False, f"{citation_number} payment_plan.monthly_amount mismatch"
    return True, "matched"


def compare_installments(prediction: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    pred_map = entry_map(prediction)
    exp_map = entry_map(expected)
    if pred_map is None:
        return False, "prediction.entries cannot be mapped by unique citation_number"
    if exp_map is None:
        return False, "answer entries are invalid"
    if set(pred_map) != set(exp_map):
        return False, "citation set mismatch"
    fields = ("full_payment_count", "total_payment_count", "final_due_date")
    for citation_number in sorted(exp_map):
        pred_plan = payment_plan(pred_map[citation_number])
        exp_plan = payment_plan(exp_map[citation_number])
        if pred_plan is None or exp_plan is None:
            return False, f"{citation_number} payment_plan is missing"
        for field in fields:
            if pred_plan.get(field) != exp_plan.get(field):
                return False, f"{citation_number} payment_plan.{field} mismatch"
        if money(pred_plan.get("final_payment_amount")) != money(exp_plan.get("final_payment_amount")):
            return False, f"{citation_number} payment_plan.final_payment_amount mismatch"
    return True, "matched"


def compare_batch_money(prediction: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    pred_totals = prediction.get("batch_totals")
    exp_totals = expected.get("batch_totals")
    if not isinstance(pred_totals, dict) or not isinstance(exp_totals, dict):
        return False, "batch_totals is not an object"
    fields = (
        "assessed_total",
        "prior_schedule_assessed_total",
        "current_schedule_assessed_total",
        "base_fine_total",
        "speed_surcharge_total",
        "traffic_school_total",
        "entered_plan_principal_total",
        "total_final_payment_amount",
    )
    for field in fields:
        if money(pred_totals.get(field)) != money(exp_totals.get(field)):
            return False, f"batch_totals.{field} mismatch"
    return True, "matched"


def compare_batch_operational(prediction: dict[str, Any], expected: dict[str, Any]) -> tuple[bool, str]:
    pred_totals = prediction.get("batch_totals")
    exp_totals = expected.get("batch_totals")
    if not isinstance(pred_totals, dict) or not isinstance(exp_totals, dict):
        return False, "batch_totals is not an object"
    fields = (
        "assessed_entry_count",
        "no_assessment_entry_count",
        "dismissed_no_assessment_count",
        "satisfied_no_assessment_count",
        "excluded_candidate_fee_count",
        "total_full_payments",
        "total_payment_count",
        "default_first_due_count",
        "below_minimum_plan_count",
        "return_to_court_review_count",
        "entries_using_prior_fee_schedule",
        "entries_using_current_fee_schedule",
        "entries_with_source_override_flags",
        "all_entered_plans_use_post_disposition_start",
    )
    for field in fields:
        if pred_totals.get(field) != exp_totals.get(field):
            return False, f"batch_totals.{field} mismatch"
    return True, "matched"


def evaluate(prediction: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    point_results = []
    earned = 0
    max_score = sum(point["weight"] for point in SCORING_POINTS)

    for point in SCORING_POINTS:
        kind = point["kind"]
        if kind == "ordered_identity":
            matched, details = compare_ordered_identity(prediction, expected)
        elif kind == "source_posture":
            matched, details = compare_source_posture(prediction, expected)
        elif kind == "entry_fields":
            matched, details = compare_entry_fields(prediction, expected, point["fields"])
        elif kind == "components_and_totals":
            matched, details = compare_components_and_totals(prediction, expected)
        elif kind == "excluded_codes":
            matched, details = compare_excluded_codes(prediction, expected)
        elif kind == "plan_start":
            matched, details = compare_plan_start(prediction, expected)
        elif kind == "installments":
            matched, details = compare_installments(prediction, expected)
        elif kind == "batch_money":
            matched, details = compare_batch_money(prediction, expected)
        elif kind == "batch_operational":
            matched, details = compare_batch_operational(prediction, expected)
        else:
            matched, details = False, "unknown scoring point kind"

        point_earned = point["weight"] if matched else 0
        earned += point_earned
        point_results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "matched": matched,
                "earned": point_earned,
                "details": details,
            }
        )

    return {
        "score": earned,
        "max_score": max_score,
        "normalized_score": round(earned / max_score if max_score else 0.0, 6),
        "points": point_results,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(point["weight"] for point in SCORING_POINTS),
                    "normalized_score": 0.0,
                    "error": "prediction file path is required as the first argument",
                },
                indent=2,
            )
        )
        return 2

    prediction_path = Path(sys.argv[1])
    expected = load_json(ANSWER_PATH)
    try:
        prediction = load_json(prediction_path)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(point["weight"] for point in SCORING_POINTS),
                    "normalized_score": 0.0,
                    "error": f"could not load prediction JSON: {exc}",
                },
                indent=2,
            )
        )
        return 1

    if not isinstance(prediction, dict):
        prediction = {}
    print(json.dumps(evaluate(prediction, expected), indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
