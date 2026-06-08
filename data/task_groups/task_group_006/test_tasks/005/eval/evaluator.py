#!/usr/bin/env python3
"""Exact-match evaluator for task_group_006 test_005."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCORING_POINTS = [
    ("SP1_identity_and_final_decision", "Correct control identity and release decision.", 2),
    ("SP2_contract_price_and_change_basis", "Correct indexed contract price and price-change basis.", 2),
    ("SP3_contract_usage_and_ceiling", "Correct contract usage, included PO set, and ceiling headroom.", 3),
    ("SP4_budget_incremental_exposure", "Correct incremental budget exposure and budget result.", 3),
    (
        "SP5_nomination_and_approval_evidence",
        "Correct nomination, approval, receipt, and matched-invoice evidence.",
        2,
    ),
    (
        "SP6_supplier_risk_and_invoice_control",
        "Correct supplier-risk context and unmatched price-variance invoice control.",
        1,
    ),
    ("SP7_actions_and_summary", "Correct required actions and release summary.", 2),
]

CENT_FIELDS = {
    "baseline_unit_price",
    "proposed_unit_price",
    "unit_price_delta",
    "incremental_subtotal",
    "estimated_tax",
    "freight_included",
    "incremental_total",
    "ceiling_amount",
    "existing_noncancelled_subtotal",
    "headroom_before_change",
    "incremental_ceiling_exposure",
    "headroom_after_change",
    "budget_cap",
    "committed_amount",
    "remaining_budget",
    "budget_after_change",
}

ONE_DECIMAL_FIELDS = {"uplift_percent"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def round_decimal(value: Any, places: str) -> float | Any:
    try:
        dec = Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return value
    return float(dec)


def normalize(value: Any, parent_key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {key: normalize(val, key) for key, val in sorted(value.items())}
    if isinstance(value, list):
        normalized = [normalize(item, parent_key) for item in value]
        if all(not isinstance(item, (dict, list)) for item in normalized):
            return sorted(normalized, key=lambda item: str(item))
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
    if parent_key in CENT_FIELDS:
        return round_decimal(value, "0.01")
    if parent_key in ONE_DECIMAL_FIELDS:
        return round_decimal(value, "0.1")
    return value


def pick(answer: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: normalize(answer.get(key), key) for key in keys}


def nested(answer: dict[str, Any], key: str, keys: list[str] | None = None) -> dict[str, Any]:
    obj = answer.get(key, {})
    if not isinstance(obj, dict):
        return {}
    if keys is None:
        return normalize(obj, key)
    return {field: normalize(obj.get(field), field) for field in keys}


def point(name: str, weight: int, got: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "weight": weight, "matched": got == expected}


def build_points(candidate: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        point(
            "SP1_identity_and_final_decision",
            2,
            pick(
                candidate,
                [
                    "task_id",
                    "control_id",
                    "as_of_date",
                    "program_id",
                    "contract_id",
                    "sku",
                    "supplier_id",
                    "source_requisition_id",
                    "nominated_po_id",
                    "decision",
                ],
            ),
            pick(
                expected,
                [
                    "task_id",
                    "control_id",
                    "as_of_date",
                    "program_id",
                    "contract_id",
                    "sku",
                    "supplier_id",
                    "source_requisition_id",
                    "nominated_po_id",
                    "decision",
                ],
            ),
        ),
        point(
            "SP2_contract_price_and_change_basis",
            2,
            nested(
                candidate,
                "change_basis",
                [
                    "change_type",
                    "redesign_reference",
                    "contract_price_type",
                    "baseline_unit_price",
                    "proposed_unit_price",
                    "unit_price_delta",
                    "uplift_percent",
                    "impacted_quantity",
                    "price_change_ok",
                ],
            ),
            nested(
                expected,
                "change_basis",
                [
                    "change_type",
                    "redesign_reference",
                    "contract_price_type",
                    "baseline_unit_price",
                    "proposed_unit_price",
                    "unit_price_delta",
                    "uplift_percent",
                    "impacted_quantity",
                    "price_change_ok",
                ],
            ),
        ),
        point(
            "SP3_contract_usage_and_ceiling",
            3,
            {
                "contract_check": nested(candidate, "contract_check"),
                "included_po_ids": nested(
                    candidate, "supporting_ids", ["included_po_ids", "excluded_cancelled_po_ids"]
                ),
            },
            {
                "contract_check": nested(expected, "contract_check"),
                "included_po_ids": nested(
                    expected, "supporting_ids", ["included_po_ids", "excluded_cancelled_po_ids"]
                ),
            },
        ),
        point(
            "SP4_budget_incremental_exposure",
            3,
            {
                "change_amounts": nested(
                    candidate,
                    "change_basis",
                    [
                        "incremental_subtotal",
                        "estimated_tax",
                        "freight_included",
                        "incremental_total",
                    ],
                ),
                "program_budget_check": nested(candidate, "program_budget_check"),
            },
            {
                "change_amounts": nested(
                    expected,
                    "change_basis",
                    [
                        "incremental_subtotal",
                        "estimated_tax",
                        "freight_included",
                        "incremental_total",
                    ],
                ),
                "program_budget_check": nested(expected, "program_budget_check"),
            },
        ),
        point(
            "SP5_nomination_and_approval_evidence",
            2,
            {
                "nomination_control": nested(candidate, "nomination_control"),
                "approval_receipt_invoice_ids": nested(
                    candidate, "supporting_ids", ["approval_event_ids", "receipt_ids", "invoice_ids"]
                ),
            },
            {
                "nomination_control": nested(expected, "nomination_control"),
                "approval_receipt_invoice_ids": nested(
                    expected, "supporting_ids", ["approval_event_ids", "receipt_ids", "invoice_ids"]
                ),
            },
        ),
        point(
            "SP6_supplier_risk_and_invoice_control",
            1,
            {
                "supplier_risk_check": nested(candidate, "supplier_risk_check"),
                "invoice_control": nested(candidate, "invoice_control"),
            },
            {
                "supplier_risk_check": nested(expected, "supplier_risk_check"),
                "invoice_control": nested(expected, "invoice_control"),
            },
        ),
        point(
            "SP7_actions_and_summary",
            2,
            pick(candidate, ["required_actions", "summary"]),
            pick(expected, ["required_actions", "summary"]),
        ),
    ]


def emit_zero(error: str) -> int:
    total_weight = sum(weight for _, _, weight in SCORING_POINTS)
    print(
        json.dumps(
            {
                "score": 0.0,
                "max_score": 1.0,
                "earned_weight": 0,
                "total_weight": total_weight,
                "error": error,
                "points": [{"name": name, "matched": False, "weight": weight} for name, _, weight in SCORING_POINTS],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: evaluator.py <candidate_answer.json>", file=sys.stderr)
        return 2

    expected_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    candidate_path = Path(sys.argv[1])

    try:
        candidate = load_json(candidate_path)
        expected = load_json(expected_path)
    except Exception as exc:  # noqa: BLE001
        return emit_zero(f"Could not load JSON: {exc}")

    if not isinstance(candidate, dict) or not isinstance(expected, dict):
        return emit_zero("Expected both JSON documents to be objects.")

    points = build_points(candidate, expected)
    total_weight = sum(point["weight"] for point in points)
    earned_weight = sum(point["weight"] for point in points if point["matched"])
    result = {
        "score": round(earned_weight / total_weight, 6),
        "max_score": 1.0,
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
