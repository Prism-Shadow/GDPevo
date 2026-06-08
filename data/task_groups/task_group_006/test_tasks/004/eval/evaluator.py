#!/usr/bin/env python3
"""Exact-match evaluator for task_group_006 test_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


POINTS = [
    {
        "name": "scope, review date, and target receipt set are correct",
        "weight": 3,
        "paths": [["task_id"], ["review"]],
    },
    {
        "name": "dashboard row identities and operational statuses are correct",
        "weight": 3,
        "paths": [["dashboard_rows"]],
        "project": [
            "receipt_id",
            "po_id",
            "invoice_id",
            "supplier_id",
            "program_id",
            "sku",
            "receipt_status",
            "po_status",
            "ap_status",
            "hold_code",
        ],
    },
    {
        "name": "AP hold, release, and not-invoiced control sets are correct",
        "weight": 2,
        "paths": [
            ["control_sets", "ap_hold_receipt_ids"],
            ["control_sets", "release_candidate_receipt_ids"],
            ["control_sets", "not_invoiced_as_of_receipt_ids"],
        ],
    },
    {
        "name": "corrected dashboard statuses and action owners are correct",
        "weight": 2,
        "paths": [["dashboard_rows"]],
        "project": ["receipt_id", "corrected_dashboard_status", "action_owner", "include_in_release_queue"],
    },
    {
        "name": "quantity variances and financial totals are correct",
        "weight": 3,
        "paths": [["dashboard_rows"], ["totals"]],
        "project": [
            "receipt_id",
            "quantity_received",
            "quantity_billed",
            "variance_quantity",
            "variance_amount_usd",
        ],
    },
    {
        "name": "supplier risk overlay is correct",
        "weight": 2,
        "paths": [
            ["dashboard_rows"],
            ["control_sets", "risk_supplier_ids"],
            ["control_sets", "open_risk_event_ids"],
        ],
        "project": ["receipt_id", "open_risk_event_ids"],
    },
    {
        "name": "source precedence and stale export corrections are correct",
        "weight": 2,
        "paths": [["source_decisions"]],
    },
    {
        "name": "follow-up action set is correct",
        "weight": 1,
        "paths": [["followup_actions"]],
    },
    {
        "name": "transfer source-precedence and AP release policies are correct",
        "weight": 3,
        "paths": [
            ["source_decisions", "transfer_precedence_policy"],
            ["source_decisions", "release_policy"],
            ["source_decisions", "chargeback_policy"],
            ["source_decisions", "payment_policy"],
            ["source_decisions", "no_receipt_policy"],
        ],
    },
    {
        "name": "chargeback, payment, and no-receipt transfer policies are complete",
        "weight": 3,
        "paths": [
            ["source_decisions", "chargeback_policy"],
            ["source_decisions", "payment_policy"],
            ["source_decisions", "no_receipt_policy"],
        ],
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def get_path(obj: Any, path: list[str]) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def normalize(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        normalized = [normalize(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    if isinstance(value, dict):
        return {key: normalize(value[key]) for key in sorted(value)}
    return value


def project_records(value: Any, keys: list[str] | None) -> Any:
    if keys is None:
        return value
    if not isinstance(value, list):
        return value
    projected = []
    for item in value:
        if not isinstance(item, dict):
            projected.append(item)
            continue
        projected.append({key: item.get(key) for key in keys})
    return projected


def evaluate(prediction: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    total_weight = sum(point["weight"] for point in POINTS)
    earned = 0
    details = []

    for point_def in POINTS:
        matched = True
        for path in point_def["paths"]:
            gold_value = project_records(get_path(gold, path), point_def.get("project"))
            pred_value = project_records(get_path(prediction, path), point_def.get("project"))
            if normalize(gold_value) != normalize(pred_value):
                matched = False
                break
        if matched:
            earned += point_def["weight"]
        details.append({"name": point_def["name"], "matched": matched, "weight": point_def["weight"]})

    return {
        "score": round(earned / total_weight, 6) if total_weight else 0.0,
        "max_score": 1.0,
        "raw_score": earned,
        "raw_max_score": total_weight,
        "points": details,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "usage: evaluator.py PREDICTION_JSON"}))
        return 2

    gold_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        prediction = load_json(Path(sys.argv[1]))
        gold = load_json(gold_path)
        result = evaluate(prediction, gold)
    except Exception as exc:  # noqa: BLE001 - evaluators should report JSON on malformed submissions.
        result = {"score": 0.0, "max_score": 1.0, "error": str(exc), "points": []}

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
