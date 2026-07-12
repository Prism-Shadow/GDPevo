#!/usr/bin/env python3
"""Exact-match evaluator for task_group_018 train_004."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cents(value: Any) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return "__invalid_number__"
    return str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def norm_fee_codes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def rows_by_case(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("case_rows")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("case_number"), str):
            result[row["case_number"]] = row
    return result


def project_rows(payload: dict[str, Any], fields: list[str]) -> dict[str, dict[str, Any]]:
    projected: dict[str, dict[str, Any]] = {}
    for case_number, row in rows_by_case(payload).items():
        projected[case_number] = {field: row.get(field) for field in fields}
    return projected


def project_currency_rows(payload: dict[str, Any], fields: list[str]) -> dict[str, dict[str, str]]:
    projected: dict[str, dict[str, str]] = {}
    for case_number, row in rows_by_case(payload).items():
        projected[case_number] = {field: cents(row.get(field)) for field in fields}
    return projected


def case_numbers_in_order(payload: dict[str, Any]) -> list[str]:
    rows = payload.get("case_rows")
    if not isinstance(rows, list):
        return []
    return [row.get("case_number") for row in rows if isinstance(row, dict)]


def aggregate_projection(payload: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    aggregate = payload.get("aggregate")
    if not isinstance(aggregate, dict):
        return {}
    projected: dict[str, Any] = {}
    for field in fields:
        value = aggregate.get(field)
        if field == "total_financial_delta":
            projected[field] = cents(value)
        elif field == "representation_mismatch_cases" and isinstance(value, list):
            projected[field] = sorted(str(item) for item in value)
        else:
            projected[field] = value
    return projected


def fee_code_projection(payload: dict[str, Any]) -> dict[str, list[str]]:
    return {
        case_number: norm_fee_codes(row.get("approved_fee_codes"))
        for case_number, row in rows_by_case(payload).items()
    }


def make_point(name: str, weight: int, goal: str, expected: Any, actual: Any) -> dict[str, Any]:
    matched = actual == expected
    return {
        "name": name,
        "goal": goal,
        "weight": weight,
        "matched": matched,
        "score": weight if matched else 0,
        "expected": expected,
        "actual": actual,
    }


def evaluate(prediction: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    points = [
        make_point(
            "case_set_and_order",
            2,
            "Correct target Marion misdemeanor docket case set in ascending case-number order.",
            case_numbers_in_order(answer),
            case_numbers_in_order(prediction),
        ),
        make_point(
            "resolved_statuses_and_dates",
            3,
            "Correct resolved status and disposition date for each target case.",
            project_rows(answer, ["resolved_status", "disposition_date"]),
            project_rows(prediction, ["resolved_status", "disposition_date"]),
        ),
        make_point(
            "disposition_classes",
            2,
            "Correct disposition class and convicted charge count for each target case.",
            project_rows(answer, ["disposition_class", "convicted_charge_count"]),
            project_rows(prediction, ["disposition_class", "convicted_charge_count"]),
        ),
        make_point(
            "representation_corrections",
            2,
            "Correct resolved counsel, defense type, and representation mismatch flag.",
            project_rows(
                answer,
                ["corrected_defense_attorney", "corrected_defense_type", "representation_mismatch"],
            ),
            project_rows(
                prediction,
                ["corrected_defense_attorney", "corrected_defense_type", "representation_mismatch"],
            ),
        ),
        make_point(
            "approved_fee_codes",
            3,
            "Correct approved fee-code set for each case, excluding unsupported or unpronounced fees.",
            fee_code_projection(answer),
            fee_code_projection(prediction),
        ),
        make_point(
            "case_financial_totals",
            3,
            "Correct current live principal and corrected approved principal to cents for each case.",
            project_currency_rows(answer, ["current_ledger_principal", "corrected_assessment_total"]),
            project_currency_rows(prediction, ["current_ledger_principal", "corrected_assessment_total"]),
        ),
        make_point(
            "financial_deltas_and_count",
            3,
            "Correct per-case financial deltas and aggregate count of cases needing financial adjustment.",
            {
                "rows": project_currency_rows(answer, ["financial_delta"]),
                "financial_adjustment_count": answer.get("aggregate", {}).get("financial_adjustment_count"),
            },
            {
                "rows": project_currency_rows(prediction, ["financial_delta"]),
                "financial_adjustment_count": prediction.get("aggregate", {}).get("financial_adjustment_count")
                if isinstance(prediction.get("aggregate"), dict)
                else None,
            },
        ),
        make_point(
            "docket_actions",
            2,
            "Correct docket action code for each case.",
            project_rows(answer, ["docket_action"]),
            project_rows(prediction, ["docket_action"]),
        ),
        make_point(
            "aggregate_rollup",
            2,
            "Correct case count, total financial delta, and representation mismatch case list.",
            aggregate_projection(answer, ["case_count", "total_financial_delta", "representation_mismatch_cases"]),
            aggregate_projection(prediction, ["case_count", "total_financial_delta", "representation_mismatch_cases"]),
        ),
    ]
    score = sum(point["score"] for point in points)
    max_score = sum(point["weight"] for point in points)
    normalized = score / max_score if max_score else 0.0
    return {
        "score": score,
        "max_score": max_score,
        "normalized_score": round(normalized, 6),
        "points": points,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: eval.sh <prediction.json>"}, indent=2))
        return 2

    prediction_path = Path(sys.argv[1])
    try:
        prediction = load_json(prediction_path)
        answer = load_json(ANSWER_PATH)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": 22,
                    "normalized_score": 0.0,
                    "error": str(exc),
                    "points": [],
                },
                indent=2,
            )
        )
        return 1

    result = evaluate(prediction, answer)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
