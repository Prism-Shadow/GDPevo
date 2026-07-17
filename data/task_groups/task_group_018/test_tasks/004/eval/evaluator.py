#!/usr/bin/env python3
"""Exact-match evaluator for task_group_018 test_004."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"
CENT = Decimal("0.01")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def money(value: Any) -> str:
    try:
        return str(Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return "__invalid_money__"


def case_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = doc.get("case_rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def rows_by_case(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in case_rows(doc):
        case_number = row.get("case_number")
        if isinstance(case_number, str):
            result[case_number] = row
    return result


def case_numbers_in_order(doc: dict[str, Any]) -> list[str | None]:
    return [row.get("case_number") for row in case_rows(doc)]


def project_rows(doc: dict[str, Any], fields: list[str]) -> dict[str, dict[str, Any]]:
    return {case_number: {field: row.get(field) for field in fields} for case_number, row in rows_by_case(doc).items()}


def project_money_rows(doc: dict[str, Any], fields: list[str]) -> dict[str, dict[str, str]]:
    return {
        case_number: {field: money(row.get(field)) for field in fields}
        for case_number, row in rows_by_case(doc).items()
    }


def fee_components(doc: dict[str, Any]) -> dict[str, list[dict[str, str | None]]]:
    result: dict[str, list[dict[str, str | None]]] = {}
    for case_number, row in rows_by_case(doc).items():
        components = row.get("approved_fee_components")
        normalized = []
        if isinstance(components, list):
            for component in components:
                if isinstance(component, dict):
                    normalized.append(
                        {
                            "fee_code": component.get("fee_code"),
                            "amount": money(component.get("amount")),
                        }
                    )
        result[case_number] = sorted(normalized, key=lambda item: str(item.get("fee_code")))
    return result


def aggregate_projection(doc: dict[str, Any]) -> dict[str, Any]:
    aggregate = doc.get("aggregate")
    if not isinstance(aggregate, dict):
        return {}
    money_fields = {
        "aggregate_live_principal",
        "aggregate_corrected_principal",
        "aggregate_principal_delta",
        "aggregate_live_amount_paid",
        "aggregate_credit_adjustment_to_paid",
        "aggregate_effective_amount_paid",
        "aggregate_corrected_balance_due",
        "aggregate_restitution_total",
        "aggregate_counsel_fee_total",
    }
    projected: dict[str, Any] = {}
    for field in [
        "case_count",
        "release_to_entry_count",
        "hold_count",
        "principal_replacement_count",
        "ledger_credit_adjustment_count",
        "counsel_fee_assessed_count",
        "counsel_fee_excluded_count",
        "held_case_numbers",
        "aggregate_live_principal",
        "aggregate_corrected_principal",
        "aggregate_principal_delta",
        "aggregate_live_amount_paid",
        "aggregate_credit_adjustment_to_paid",
        "aggregate_effective_amount_paid",
        "aggregate_corrected_balance_due",
        "aggregate_restitution_total",
        "aggregate_counsel_fee_total",
    ]:
        value = aggregate.get(field)
        if field in money_fields:
            projected[field] = money(value)
        elif field == "held_case_numbers" and isinstance(value, list):
            projected[field] = sorted(str(item) for item in value)
        else:
            projected[field] = value
    return projected


def make_point(point_id: str, weight: int, goal: str, expected: Any, actual: Any) -> dict[str, Any]:
    matched = actual == expected
    return {
        "id": point_id,
        "goal": goal,
        "weight": weight,
        "matched": matched,
        "earned": weight if matched else 0,
        "expected": expected,
        "actual": actual,
    }


def evaluate(prediction: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    points = [
        make_point(
            "SP001",
            1,
            "Correct task metadata, audit date, and currency.",
            {key: answer.get(key) for key in ["task_id", "county", "audit_date", "currency"]},
            {key: prediction.get(key) for key in ["task_id", "county", "audit_date", "currency"]},
        ),
        make_point(
            "SP002",
            2,
            "Correct target Benton post-disposition criminal case set in ascending case-number order.",
            case_numbers_in_order(answer),
            case_numbers_in_order(prediction),
        ),
        make_point(
            "SP003",
            3,
            "Correct statuses, disposition dates, assessment basis dates, and source-conflict codes.",
            project_rows(
                answer,
                ["resolved_status", "disposition_date", "assessment_basis_date", "source_conflict_code"],
            ),
            project_rows(
                prediction,
                ["resolved_status", "disposition_date", "assessment_basis_date", "source_conflict_code"],
            ),
        ),
        make_point(
            "SP004",
            3,
            "Correct defense attorney, defense type, and conditional counsel-fee treatment.",
            project_rows(
                answer,
                ["final_defense_attorney", "final_defense_type", "counsel_fee_treatment"],
            ),
            project_rows(
                prediction,
                ["final_defense_attorney", "final_defense_type", "counsel_fee_treatment"],
            ),
        ),
        make_point(
            "SP005",
            3,
            "Correct approved fee component codes and amounts, including effective-date and counsel-cost rows.",
            fee_components(answer),
            fee_components(prediction),
        ),
        make_point(
            "SP006",
            3,
            "Correct restitution amounts, corrected principal totals, and corrected balances due.",
            project_money_rows(
                answer,
                ["restitution_amount", "corrected_principal_total", "corrected_balance_due"],
            ),
            project_money_rows(
                prediction,
                ["restitution_amount", "corrected_principal_total", "corrected_balance_due"],
            ),
        ),
        make_point(
            "SP007",
            3,
            "Correct live ledger principal, live paid credit, credit adjustment, effective paid credit, and principal delta.",
            project_money_rows(
                answer,
                [
                    "live_ledger_principal",
                    "live_amount_paid",
                    "ledger_credit_adjustment_to_paid",
                    "effective_amount_paid",
                    "principal_delta",
                ],
            ),
            project_money_rows(
                prediction,
                [
                    "live_ledger_principal",
                    "live_amount_paid",
                    "ledger_credit_adjustment_to_paid",
                    "effective_amount_paid",
                    "principal_delta",
                ],
            ),
        ),
        make_point(
            "SP008",
            2,
            "Correct release-to-entry flags, hold reasons, and next action codes.",
            project_rows(answer, ["release_to_entry", "hold_reason_code", "next_action_code"]),
            project_rows(prediction, ["release_to_entry", "hold_reason_code", "next_action_code"]),
        ),
        make_point(
            "SP009",
            3,
            "Correct aggregate counts, held-case set, financial rollups, credit-adjustment rollups, and counsel-fee totals.",
            aggregate_projection(answer),
            aggregate_projection(prediction),
        ),
    ]
    score = sum(point["earned"] for point in points)
    max_score = sum(point["weight"] for point in points)
    return {
        "score": score,
        "max_score": max_score,
        "normalized_score": round(score / max_score if max_score else 0.0, 6),
        "scoring_points": points,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: evaluator.py <prediction_json>"}, indent=2))
        return 2
    prediction_path = Path(sys.argv[1]).expanduser()
    max_score = 23
    try:
        prediction = load_json(prediction_path)
        answer = load_json(ANSWER_PATH)
        result = evaluate(prediction, answer)
    except json.JSONDecodeError as exc:
        result = {
            "score": 0,
            "max_score": max_score,
            "normalized_score": 0.0,
            "error": f"invalid JSON: {exc}",
            "scoring_points": [],
        }
    except Exception as exc:
        result = {
            "score": 0,
            "max_score": max_score,
            "normalized_score": 0.0,
            "error": str(exc),
            "scoring_points": [],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
