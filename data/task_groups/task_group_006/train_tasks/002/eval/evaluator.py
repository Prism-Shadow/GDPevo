#!/usr/bin/env python3
"""Exact-match evaluator for task_group_006 train_002."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, list):
        normalized = [normalize(item) for item in value]
        if all(isinstance(item, (str, int, float, bool, type(None))) for item in normalized):
            return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
        if all(isinstance(item, dict) and "po_line_id" in item for item in normalized):
            return sorted(normalized, key=lambda item: item["po_line_id"])
        return normalized
    if isinstance(value, dict):
        return {key: normalize(value[key]) for key in sorted(value)}
    return value


def get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


POINTS = [
    {
        "name": "SP001_batch_identity",
        "weight": 2,
        "paths": [
            "task_id",
            "batch_id",
            "inspection_summary.po_id",
            "inspection_summary.program_id",
            "inspection_summary.supplier_id",
            "inspection_summary.supplier_name",
            "inspection_summary.warehouse_id",
            "inspection_summary.receipt_date",
            "inspection_summary.packing_slip",
            "inspection_summary.receiver",
        ],
    },
    {
        "name": "SP002_line_quantity_reconciliation",
        "weight": 3,
        "paths": [
            "line_reconciliation.0.po_line_id",
            "line_reconciliation.0.sku",
            "line_reconciliation.0.ordered_qty",
            "line_reconciliation.0.received_qty",
            "line_reconciliation.0.rejected_qty",
            "line_reconciliation.0.billed_qty",
            "line_reconciliation.0.short_qty_vs_po",
            "line_reconciliation.0.unreceived_billed_qty",
            "line_reconciliation.0.receipt_completion_ratio",
        ],
    },
    {
        "name": "SP003_invoice_hold_status",
        "weight": 2,
        "paths": [
            "invoice_review.invoice_id",
            "invoice_review.invoice_status",
            "invoice_review.hold_code",
            "invoice_review.receipt_status",
            "invoice_review.po_status",
            "invoice_review.exception_codes",
        ],
    },
    {
        "name": "SP004_financial_variance",
        "weight": 2,
        "paths": [
            "financials.received_goods_value",
            "financials.unreceived_goods_value",
            "financials.invoice_subtotal",
            "financials.invoice_freight",
            "financials.invoice_tax",
            "financials.invoice_total",
        ],
    },
    {
        "name": "SP005_business_disposition",
        "weight": 3,
        "paths": [
            "decision.batch_disposition",
            "decision.ap_action",
            "decision.receiving_action",
            "decision.supplier_action",
        ],
    },
    {
        "name": "SP006_supplier_risk_context",
        "weight": 1,
        "paths": [
            "supplier_risk_context.supplier_risk_rating",
            "supplier_risk_context.has_open_supplier_risk",
            "supplier_risk_context.open_supplier_risk_event_ids",
        ],
    },
    {
        "name": "SP007_source_record_set",
        "weight": 2,
        "paths": [
            "evidence.endpoint_record_ids",
            "evidence.task_payloads_reviewed",
        ],
    },
    {
        "name": "SP008_contract_price_consistency",
        "weight": 2,
        "paths": [
            "line_reconciliation.0.po_unit_price",
            "line_reconciliation.0.contract_unit_price",
            "line_reconciliation.0.invoice_unit_price",
            "line_reconciliation.0.contract_price_match",
        ],
    },
]


def point_matches(expected: dict[str, Any], actual: dict[str, Any], paths: list[str]) -> bool:
    for path in paths:
        if normalize(get_path(actual, path)) != normalize(get_path(expected, path)):
            return False
    return True


def evaluate(prediction_path: Path) -> dict[str, Any]:
    expected = load_json(ANSWER_PATH)
    try:
        actual = load_json(prediction_path)
    except Exception as exc:
        points = [{"name": point["name"], "matched": False, "weight": point["weight"]} for point in POINTS]
        return {
            "score": 0.0,
            "max_score": 1.0,
            "points": points,
            "error": f"Could not parse prediction JSON: {exc}",
        }

    total_weight = sum(point["weight"] for point in POINTS)
    scored_points = []
    score = 0.0
    for point in POINTS:
        matched = point_matches(expected, actual, point["paths"])
        scored_points.append({"name": point["name"], "matched": matched, "weight": point["weight"]})
        if matched:
            score += point["weight"] / total_weight

    return {"score": round(score, 10), "max_score": 1.0, "points": scored_points}


def main() -> None:
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "Usage: evaluator.py <prediction.json>"}))
        raise SystemExit(2)
    result = evaluate(Path(sys.argv[1]))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
