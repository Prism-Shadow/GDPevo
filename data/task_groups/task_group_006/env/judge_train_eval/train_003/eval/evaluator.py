#!/usr/bin/env python3
"""Exact-match evaluator for task_group_006 train_003."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCORING_POINTS = [
    ("SP001", "Correct task identity, close date, and target invoice set.", 2),
    ("SP002", "Correct invoice-level hold and release decisions.", 3),
    ("SP003", "Correct receipt quantity reconciliation and variance percentages.", 2),
    ("SP004", "Correct invoice totals, scheduled payment amounts, and net balance impacts.", 2),
    ("SP005", "Correct supplier names and vendor-balance reconciliation rows.", 2),
    ("SP006", "Correct controlled reason-code sets for each invoice.", 1),
    ("SP007", "Correct AX17 and NOVA program close totals.", 3),
    ("SP008", "Correct payment hold/release queues and total close balance.", 2),
]


NUMERIC_PLACES = {
    "quantity_billed": 2,
    "quantity_received": 2,
    "quantity_variance": 2,
    "quantity_variance_pct": 1,
    "invoice_total": 2,
    "scheduled_payment_amount": 2,
    "net_balance_impact": 2,
    "opening_balance": 2,
    "scheduled_payments": 2,
    "held_invoice_total": 2,
    "releasable_invoice_total": 2,
    "close_balance": 2,
    "held_total": 2,
    "released_total": 2,
    "net_close_balance": 2,
    "total_close_balance": 2,
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def round_value(value: Any, field: str) -> Any:
    if field in NUMERIC_PLACES and isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), NUMERIC_PLACES[field])
    return value


def rows_by_key(payload: dict[str, Any], list_key: str, row_key: str) -> dict[str, dict[str, Any]]:
    rows = payload.get(list_key)
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get(row_key), str):
            result[row[row_key]] = row
    return result


def compare_row_fields(
    expected_rows: dict[str, dict[str, Any]],
    actual_rows: dict[str, dict[str, Any]],
    fields: list[str],
) -> bool:
    if set(expected_rows) != set(actual_rows):
        return False
    for row_id, expected in expected_rows.items():
        actual = actual_rows[row_id]
        for field in fields:
            expected_value = round_value(expected.get(field), field)
            actual_value = round_value(actual.get(field), field)
            if actual_value != expected_value:
                return False
    return True


def sorted_reason_rows(rows: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row_id, row in rows.items():
        reason_codes = row.get("reason_codes")
        if not isinstance(reason_codes, list) or not all(isinstance(item, str) for item in reason_codes):
            return {}
        result[row_id] = sorted(reason_codes)
    return result


def emit_zero(error: str) -> int:
    total_weight = sum(point[2] for point in SCORING_POINTS)
    print(
        json.dumps(
            {
                "score": 0.0,
                "max_score": 1.0,
                "total_weight": total_weight,
                "earned_weight": 0,
                "error": error,
                "points": [
                    {"id": point_id, "name": goal, "matched": False, "weight": weight}
                    for point_id, goal, weight in SCORING_POINTS
                ],
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: evaluator.py <candidate_answer.json>", file=sys.stderr)
        return 2

    script_dir = Path(__file__).resolve().parent
    expected_path = script_dir.parent / "output" / "answer.json"
    candidate_path = Path(sys.argv[1])

    try:
        expected = load_json(expected_path)
        actual = load_json(candidate_path)
    except Exception as exc:
        return emit_zero(f"Could not load JSON: {exc}")

    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return emit_zero("Expected both JSON documents to be objects.")

    expected_invoices = rows_by_key(expected, "invoice_decisions", "invoice_id")
    actual_invoices = rows_by_key(actual, "invoice_decisions", "invoice_id")
    expected_vendors = rows_by_key(expected, "vendor_balances", "supplier_id")
    actual_vendors = rows_by_key(actual, "vendor_balances", "supplier_id")
    expected_programs = rows_by_key(expected, "program_summary", "program_id")
    actual_programs = rows_by_key(actual, "program_summary", "program_id")

    checks = {
        "SP001": (
            actual.get("task_id") == expected.get("task_id")
            and actual.get("close_date") == expected.get("close_date")
            and set(actual_invoices) == set(expected_invoices)
        ),
        "SP002": compare_row_fields(
            expected_invoices,
            actual_invoices,
            [
                "program_id",
                "po_id",
                "supplier_id",
                "invoice_status",
                "hold_decision",
                "hold_code",
                "release_to_payment",
            ],
        ),
        "SP003": compare_row_fields(
            expected_invoices,
            actual_invoices,
            ["quantity_billed", "quantity_received", "quantity_variance", "quantity_variance_pct"],
        ),
        "SP004": compare_row_fields(
            expected_invoices,
            actual_invoices,
            ["invoice_total", "scheduled_payment_amount", "net_balance_impact"],
        ),
        "SP005": compare_row_fields(
            expected_vendors,
            actual_vendors,
            [
                "supplier_name",
                "opening_balance",
                "invoice_total",
                "scheduled_payments",
                "held_invoice_total",
                "releasable_invoice_total",
                "close_balance",
                "balance_status",
            ],
        ),
        "SP006": sorted_reason_rows(actual_invoices) == sorted_reason_rows(expected_invoices),
        "SP007": compare_row_fields(
            expected_programs,
            actual_programs,
            ["invoice_count", "invoice_total", "held_total", "released_total", "net_close_balance"],
        ),
        "SP008": (
            actual.get("payment_hold_queue") == expected.get("payment_hold_queue")
            and actual.get("payment_release_queue") == expected.get("payment_release_queue")
            and round_value(actual.get("total_close_balance"), "total_close_balance")
            == round_value(expected.get("total_close_balance"), "total_close_balance")
        ),
    }

    total_weight = sum(point[2] for point in SCORING_POINTS)
    earned_weight = sum(weight for point_id, _, weight in SCORING_POINTS if checks[point_id])
    result = {
        "score": round(earned_weight / total_weight, 6),
        "max_score": 1.0,
        "total_weight": total_weight,
        "earned_weight": earned_weight,
        "points": [
            {
                "id": point_id,
                "name": goal,
                "matched": bool(checks[point_id]),
                "weight": weight,
            }
            for point_id, goal, weight in SCORING_POINTS
        ],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
