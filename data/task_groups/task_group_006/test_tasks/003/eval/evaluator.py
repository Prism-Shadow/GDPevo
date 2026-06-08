#!/usr/bin/env python3
"""Exact-match evaluator for task_group_006 test_003."""

from __future__ import annotations

import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "output" / "answer.json"

SCORING_POINTS = [
    ("SP001_scope_and_requirement", 1),
    ("SP002_program_budget_and_shortlist_sets", 2),
    ("SP003_candidate_api_status_and_risk", 2),
    ("SP004_candidate_sourcing_decisions", 2),
    ("SP005_selected_supplier_commercial_support", 2),
    ("SP006_nomination_gate_signoffs_and_decision", 2),
    ("SP007_actions_and_source_records", 1),
    ("SP008_sourcing_gate_transfer_controls", 3),
    ("SP009_commercial_backup_transfer_controls", 3),
]

CENT_FIELDS = {"budget_headroom_usd", "quote_unit_price_usd", "invoice_total_usd"}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cents(value: Any) -> Any:
    try:
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return value


def normalize(value: Any, parent_key: str | None = None) -> Any:
    if parent_key in CENT_FIELDS:
        return cents(value)
    if isinstance(value, dict):
        return {key: normalize(val, key) for key, val in sorted(value.items())}
    if isinstance(value, list):
        normalized = [normalize(item, parent_key) for item in value]
        if all(not isinstance(item, (dict, list)) for item in normalized):
            return sorted(normalized, key=lambda item: str(item))
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
    return value


def pick(answer: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: normalize(answer.get(key), key) for key in keys}


def nested(answer: dict[str, Any], key: str, keys: list[str] | None = None) -> dict[str, Any]:
    value = answer.get(key)
    if not isinstance(value, dict):
        return {}
    if keys is None:
        return normalize(value, key)
    return {field: normalize(value.get(field), field) for field in keys}


def rows_by_supplier(answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = answer.get("candidate_screening")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("supplier_id"), str):
            result[row["supplier_id"]] = row
    return result


def supplier_fields(answer: dict[str, Any], fields: list[str]) -> dict[str, dict[str, Any]]:
    rows = rows_by_supplier(answer)
    return {
        supplier_id: {field: normalize(row.get(field), field) for field in fields}
        for supplier_id, row in sorted(rows.items())
    }


def point(name: str, matched: bool, weight: int) -> dict[str, Any]:
    return {"name": name, "matched": bool(matched), "weight": weight}


def build_points(candidate: dict[str, Any], gold: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        point(
            "SP001_scope_and_requirement",
            pick(candidate, ["task_id", "program_id", "as_of_date", "rfq_packet_ref", "sku"])
            == pick(gold, ["task_id", "program_id", "as_of_date", "rfq_packet_ref", "sku"])
            and nested(candidate, "requirement") == nested(gold, "requirement"),
            1,
        ),
        point(
            "SP002_program_budget_and_shortlist_sets",
            nested(candidate, "program_summary") == nested(gold, "program_summary")
            and pick(candidate, ["shortlist_supplier_ids", "excluded_supplier_ids", "selected_supplier_id"])
            == pick(gold, ["shortlist_supplier_ids", "excluded_supplier_ids", "selected_supplier_id"]),
            2,
        ),
        point(
            "SP003_candidate_api_status_and_risk",
            supplier_fields(
                candidate,
                [
                    "supplier_name",
                    "supplier_status",
                    "risk_rating",
                    "existing_commercial_basis_id",
                    "open_or_monitoring_risk_event_ids",
                ],
            )
            == supplier_fields(
                gold,
                [
                    "supplier_name",
                    "supplier_status",
                    "risk_rating",
                    "existing_commercial_basis_id",
                    "open_or_monitoring_risk_event_ids",
                ],
            ),
            2,
        ),
        point(
            "SP004_candidate_sourcing_decisions",
            supplier_fields(
                candidate,
                [
                    "memo_technical_fit",
                    "memo_capacity_units",
                    "quote_unit_price_usd",
                    "shortlist_decision",
                    "blocker_codes",
                ],
            )
            == supplier_fields(
                gold,
                [
                    "memo_technical_fit",
                    "memo_capacity_units",
                    "quote_unit_price_usd",
                    "shortlist_decision",
                    "blocker_codes",
                ],
            ),
            2,
        ),
        point(
            "SP005_selected_supplier_commercial_support",
            nested(candidate, "commercial_support") == nested(gold, "commercial_support"),
            2,
        ),
        point(
            "SP006_nomination_gate_signoffs_and_decision",
            nested(candidate, "nomination_gate") == nested(gold, "nomination_gate"),
            2,
        ),
        point(
            "SP007_actions_and_source_records",
            pick(candidate, ["recommended_actions", "source_record_ids"])
            == pick(gold, ["recommended_actions", "source_record_ids"]),
            1,
        ),
        point(
            "SP008_sourcing_gate_transfer_controls",
            nested(candidate, "transfer_gate_controls", ["trar_gate_policy", "nomination_policy"])
            == nested(gold, "transfer_gate_controls", ["trar_gate_policy", "nomination_policy"]),
            3,
        ),
        point(
            "SP009_commercial_backup_transfer_controls",
            nested(candidate, "transfer_gate_controls", ["commercial_policy", "backup_policy"])
            == nested(gold, "transfer_gate_controls", ["commercial_policy", "backup_policy"]),
            3,
        ),
    ]


def zero_result(error: str) -> dict[str, Any]:
    total = sum(weight for _, weight in SCORING_POINTS)
    return {
        "score": 0.0,
        "max_score": 1.0,
        "earned_weight": 0,
        "total_weight": total,
        "error": error,
        "points": [{"name": name, "matched": False, "weight": weight} for name, weight in SCORING_POINTS],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps(zero_result("usage: evaluator.py PREDICTION_JSON"), indent=2, sort_keys=True))
        return 2

    try:
        candidate = load_json(Path(sys.argv[1]))
        gold = load_json(GOLD_PATH)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps(zero_result(f"Could not parse input JSON: {exc}"), indent=2, sort_keys=True))
        return 0

    if not isinstance(candidate, dict) or not isinstance(gold, dict):
        result = zero_result("Both prediction and gold answer must be JSON objects.")
    else:
        points = build_points(candidate, gold)
        total = sum(point_item["weight"] for point_item in points)
        earned = sum(point_item["weight"] for point_item in points if point_item["matched"])
        result = {
            "score": round(earned / total, 6) if total else 0.0,
            "max_score": 1.0,
            "earned_weight": earned,
            "total_weight": total,
            "points": points,
        }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
