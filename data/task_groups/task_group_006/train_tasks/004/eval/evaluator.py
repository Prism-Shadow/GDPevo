#!/usr/bin/env python3
"""Exact-match evaluator for task_group_006 train_004."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


TOTAL_WEIGHT = 15
CENT_FIELDS = {
    "unit_price",
    "ceiling_amount",
    "noncancelled_subtotal",
    "headroom_before_change",
    "requested_subtotal",
    "headroom_after_change",
    "budget_cap",
    "committed_amount",
    "remaining_budget",
    "requested_tax",
    "requested_total",
    "budget_after_change",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cents(value: Any) -> float | Any:
    try:
        dec = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
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
        return cents(value)
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


def score_point(name: str, weight: int, got: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "weight": weight, "matched": got == expected}


def build_points(candidate: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        score_point(
            "SP1_identity_and_final_decision",
            2,
            pick(
                candidate,
                ["change_request_id", "program_id", "contract_id", "sku", "supplier_id", "variant_code", "decision"],
            ),
            pick(
                expected,
                ["change_request_id", "program_id", "contract_id", "sku", "supplier_id", "variant_code", "decision"],
            ),
        ),
        score_point(
            "SP2_contract_status_price_and_quantity",
            2,
            nested(
                candidate,
                "contract_check",
                [
                    "contract_status",
                    "price_type",
                    "unit_price",
                    "ceiling_amount",
                    "requested_quantity",
                    "requested_subtotal",
                    "ceiling_ok",
                ],
            ),
            nested(
                expected,
                "contract_check",
                [
                    "contract_status",
                    "price_type",
                    "unit_price",
                    "ceiling_amount",
                    "requested_quantity",
                    "requested_subtotal",
                    "ceiling_ok",
                ],
            ),
        ),
        score_point(
            "SP3_contract_usage_and_headroom",
            3,
            nested(
                candidate,
                "contract_check",
                ["noncancelled_subtotal", "headroom_before_change", "headroom_after_change"],
            ),
            nested(
                expected,
                "contract_check",
                ["noncancelled_subtotal", "headroom_before_change", "headroom_after_change"],
            ),
        ),
        score_point(
            "SP4_program_budget_exposure",
            3,
            nested(candidate, "program_budget_check"),
            nested(expected, "program_budget_check"),
        ),
        score_point(
            "SP5_requisition_approval_state",
            2,
            nested(candidate, "approval_check"),
            nested(expected, "approval_check"),
        ),
        score_point(
            "SP6_supplier_risk_context_and_supporting_ids",
            1,
            {
                "supplier_risk_check": nested(candidate, "supplier_risk_check"),
                "supporting_ids": nested(candidate, "supporting_ids"),
            },
            {
                "supplier_risk_check": nested(expected, "supplier_risk_check"),
                "supporting_ids": nested(expected, "supporting_ids"),
            },
        ),
        score_point(
            "SP7_hold_actions_and_summary",
            2,
            pick(candidate, ["required_actions", "summary"]),
            pick(expected, ["required_actions", "summary"]),
        ),
    ]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: evaluator.py <candidate_answer.json>", file=sys.stderr)
        return 2

    candidate_path = Path(sys.argv[1])
    expected_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"

    try:
        candidate = load_json(candidate_path)
        expected = load_json(expected_path)
    except Exception as exc:  # noqa: BLE001
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "earned_weight": 0,
            "total_weight": TOTAL_WEIGHT,
            "error": f"Could not parse input JSON: {exc}",
            "points": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if not isinstance(candidate, dict) or not isinstance(expected, dict):
        points: list[dict[str, Any]] = []
        earned = 0
    else:
        points = build_points(candidate, expected)
        earned = sum(point["weight"] for point in points if point["matched"])

    result = {
        "score": round(earned / TOTAL_WEIGHT, 6),
        "max_score": 1.0,
        "earned_weight": earned,
        "total_weight": TOTAL_WEIGHT,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
