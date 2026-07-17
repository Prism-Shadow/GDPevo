#!/usr/bin/env python3
"""Evaluator for task_group_018 train_005."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
ANSWER_PATH = TASK_DIR / "output" / "answer.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def money(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return None


def one_decimal(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return None


def records_by_case(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = payload.get("records")
    if not isinstance(records, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, dict) and isinstance(record.get("case_number"), str):
            result[record["case_number"]] = record
    return result


def sorted_case_numbers(payload: dict[str, Any]) -> list[str]:
    records = payload.get("records")
    if not isinstance(records, list):
        return []
    return [record.get("case_number") for record in records if isinstance(record, dict)]


def scalar(record: dict[str, Any], field: str, kind: str = "raw") -> Any:
    value = record.get(field)
    if kind == "money":
        return money(value)
    if kind == "one_decimal":
        return one_decimal(value)
    return value


def aggregate_value(payload: dict[str, Any], field: str, kind: str = "raw") -> Any:
    aggregate = payload.get("aggregate")
    if not isinstance(aggregate, dict):
        return None
    value = aggregate.get(field)
    if kind == "money":
        return money(value)
    return value


def compare_case_fields(
    prediction: dict[str, Any],
    answer: dict[str, Any],
    case_fields: dict[str, list[tuple[str, str]]],
) -> tuple[bool, dict[str, Any], dict[str, Any]]:
    pred_records = records_by_case(prediction)
    ans_records = records_by_case(answer)
    expected: dict[str, Any] = {}
    actual: dict[str, Any] = {}
    for case_number, fields in case_fields.items():
        expected[case_number] = {}
        actual[case_number] = {}
        ans_record = ans_records.get(case_number, {})
        pred_record = pred_records.get(case_number, {})
        for field, kind in fields:
            expected[case_number][field] = scalar(ans_record, field, kind)
            actual[case_number][field] = scalar(pred_record, field, kind)
    return actual == expected, expected, actual


def evaluate(prediction: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    points: list[dict[str, Any]] = []

    def add_point(point_id: str, goal: str, weight: int, passed: bool, expected: Any, actual: Any) -> None:
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "passed": bool(passed),
                "expected": expected,
                "actual": actual,
            }
        )

    expected_order = sorted_case_numbers(answer)
    actual_order = sorted_case_numbers(prediction)
    expected_target = {
        "task_id": answer.get("task_id"),
        "county": answer.get("county"),
        "review_order_date": answer.get("review_order_date"),
        "case_numbers_in_order": expected_order,
        "included_case_count": aggregate_value(answer, "included_case_count"),
    }
    actual_target = {
        "task_id": prediction.get("task_id"),
        "county": prediction.get("county"),
        "review_order_date": prediction.get("review_order_date"),
        "case_numbers_in_order": actual_order,
        "included_case_count": aggregate_value(prediction, "included_case_count"),
    }
    add_point(
        "SP01",
        "Correct included Wasco review matters, ordering, county, task id, and review date.",
        2,
        actual_target == expected_target,
        expected_target,
        actual_target,
    )

    passed, expected, actual = compare_case_fields(
        prediction,
        answer,
        {
            "23-WAS-00144": [("source_conflict_code", "raw")],
            "23-WAS-01002": [("source_conflict_code", "raw")],
            "24-WAS-00290": [("source_conflict_code", "raw")],
            "24-WAS-01001": [("source_conflict_code", "raw")],
            "24-WAS-01003": [("source_conflict_code", "raw")],
        },
    )
    add_point(
        "SP02",
        "Correct source-conflict and packet-exception codes for every included case.",
        2,
        passed,
        expected,
        actual,
    )

    balance_fields = [
        ("ledger_balance_before_adjustment", "money"),
        ("correction_amount", "money"),
        ("corrected_balance_due", "money"),
    ]
    passed, expected, actual = compare_case_fields(
        prediction,
        answer,
        {
            "23-WAS-00144": balance_fields,
            "23-WAS-01002": balance_fields,
            "24-WAS-00290": balance_fields,
            "24-WAS-01001": balance_fields,
            "24-WAS-01003": balance_fields,
        },
    )
    expected["aggregate"] = {
        "corrected_total_balance_due": aggregate_value(answer, "corrected_total_balance_due", "money")
    }
    actual["aggregate"] = {
        "corrected_total_balance_due": aggregate_value(prediction, "corrected_total_balance_due", "money")
    }
    add_point(
        "SP03",
        "Correct live ledger balances, packet credits, corrected balances, and aggregate corrected balance.",
        3,
        actual == expected,
        expected,
        actual,
    )

    passed, expected, actual = compare_case_fields(
        prediction,
        answer,
        {
            "23-WAS-01002": [
                ("payment_plan_action", "raw"),
                ("monthly_payment_amount", "money"),
                ("installment_count", "raw"),
                ("final_payment_amount", "money"),
                ("first_due_date", "raw"),
                ("final_due_date", "raw"),
            ]
        },
    )
    expected["aggregate"] = {"revised_plan_case_numbers": aggregate_value(answer, "revised_plan_case_numbers")}
    actual["aggregate"] = {"revised_plan_case_numbers": aggregate_value(prediction, "revised_plan_case_numbers")}
    add_point(
        "SP04",
        "Correct revised ability-to-pay plan for the approved DUI petition.",
        3,
        actual == expected,
        expected,
        actual,
    )

    passed, expected, actual = compare_case_fields(
        prediction,
        answer,
        {
            "24-WAS-00290": [
                ("payment_plan_action", "raw"),
                ("monthly_payment_amount", "money"),
                ("installment_count", "raw"),
                ("final_payment_amount", "money"),
                ("first_due_date", "raw"),
                ("final_due_date", "raw"),
            ],
            "24-WAS-01001": [
                ("payment_plan_action", "raw"),
                ("monthly_payment_amount", "money"),
                ("installment_count", "raw"),
                ("final_payment_amount", "money"),
                ("first_due_date", "raw"),
                ("final_due_date", "raw"),
            ],
        },
    )
    add_point(
        "SP05",
        "Correct remaining-plan treatment for the open restitution case and active warrant-calendar plan.",
        2,
        passed,
        expected,
        actual,
    )

    passed, expected, actual = compare_case_fields(
        prediction,
        answer,
        {
            "23-WAS-00144": [("restitution_status", "raw")],
            "23-WAS-01002": [("restitution_status", "raw")],
            "24-WAS-00290": [("restitution_status", "raw")],
            "24-WAS-01001": [("restitution_status", "raw")],
            "24-WAS-01003": [("restitution_status", "raw")],
        },
    )
    add_point(
        "SP06",
        "Correct restitution status across no-restitution, open-restitution, and disbursed-restitution matters.",
        2,
        passed,
        expected,
        actual,
    )

    passed, expected, actual = compare_case_fields(
        prediction,
        answer,
        {
            "23-WAS-01002": [
                ("community_service_status", "raw"),
                ("community_service_remaining_hours", "one_decimal"),
            ],
            "24-WAS-00290": [
                ("community_service_status", "raw"),
                ("community_service_remaining_hours", "one_decimal"),
            ],
            "24-WAS-01003": [
                ("community_service_status", "raw"),
                ("community_service_remaining_hours", "one_decimal"),
            ],
        },
    )
    add_point(
        "SP07",
        "Correct community-service completion status and remaining hours for the affected cases.",
        2,
        passed,
        expected,
        actual,
    )

    passed, expected, actual = compare_case_fields(
        prediction,
        answer,
        {
            "23-WAS-00144": [("financial_status", "raw"), ("next_action", "raw")],
            "23-WAS-01002": [("financial_status", "raw"), ("next_action", "raw")],
            "24-WAS-00290": [("financial_status", "raw"), ("next_action", "raw")],
            "24-WAS-01001": [("financial_status", "raw"), ("next_action", "raw")],
            "24-WAS-01003": [("financial_status", "raw"), ("next_action", "raw")],
        },
    )
    expected["aggregate"] = {
        "return_to_court_count": aggregate_value(answer, "return_to_court_count"),
        "post_credit_case_numbers": aggregate_value(answer, "post_credit_case_numbers"),
    }
    actual["aggregate"] = {
        "return_to_court_count": aggregate_value(prediction, "return_to_court_count"),
        "post_credit_case_numbers": aggregate_value(prediction, "post_credit_case_numbers"),
    }
    add_point(
        "SP08",
        "Correct financial status, next-action routing, return-to-court count, and receipt-credit closeout set.",
        3,
        actual == expected,
        expected,
        actual,
    )

    max_score = sum(point["weight"] for point in points)
    score = sum(point["weight"] for point in points if point["passed"])
    return {
        "score": score,
        "max_score": max_score,
        "normalized_score": round(score / max_score if max_score else 0.0, 6),
        "points": points,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: evaluator.py <prediction.json>"}, indent=2))
        return 2
    prediction_path = Path(sys.argv[1])
    if not prediction_path.is_absolute():
        prediction_path = Path.cwd() / prediction_path
    try:
        prediction = load_json(prediction_path)
        answer = load_json(ANSWER_PATH)
    except Exception as exc:
        print(json.dumps({"error": str(exc), "score": 0, "max_score": 19, "normalized_score": 0.0}, indent=2))
        return 1
    result = evaluate(prediction, answer)
    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
