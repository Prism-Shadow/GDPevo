#!/usr/bin/env python3
"""Exact-match evaluator for task_group_006 test_001."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


POINTS = [
    {
        "name": "target IDs and review date are correct",
        "weight": 3,
        "paths": [["task_id"], ["review_as_of"], ["target_ids"]],
    },
    {
        "name": "receipt inclusion and exclusion controls are correct",
        "weight": 3,
        "paths": [["receipt_controls"]],
        "project": ["receipt_id", "po_id", "relation_to_target", "scope_decision", "primary_reason", "receipt_status"],
    },
    {
        "name": "target quantity and contract-price reconciliation is correct",
        "weight": 2,
        "paths": [["target_reconciliation"]],
    },
    {
        "name": "invoice decisions and primary reasons are correct",
        "weight": 2,
        "paths": [["invoice_controls"]],
        "project": ["invoice_id", "po_id", "decision", "primary_reason", "release_to_payment"],
    },
    {
        "name": "financial release, duplicate exposure, and payment totals are correct",
        "weight": 3,
        "paths": [
            ["summary", "release_invoice_ids"],
            ["summary", "review_invoice_ids"],
            ["summary", "scheduled_payment_ids"],
            ["summary", "net_release_total"],
            ["summary", "duplicate_payment_exposure"],
            ["summary", "price_variance_subtotal"],
        ],
    },
    {
        "name": "invoice receipt scope and exclusions are correct",
        "weight": 2,
        "paths": [["invoice_controls"]],
        "project": ["invoice_id", "receipt_ids_in_scope", "excluded_receipt_ids"],
    },
    {
        "name": "source precedence and supplier risk context are correct",
        "weight": 2,
        "paths": [
            ["supplier_context"],
            ["summary", "in_scope_receipt_ids"],
            ["summary", "excluded_receipt_ids"],
            ["summary", "non_scope_export_receipt_ids"],
            ["summary", "authoritative_sources"],
            ["summary", "supporting_only_sources"],
        ],
    },
    {"name": "follow-up action set is correct", "weight": 1, "paths": [["summary", "followup_actions"]]},
    {
        "name": "AP release and duplicate-invoice transfer controls are correct",
        "weight": 3,
        "paths": [["transfer_controls", "ap_release_policy"], ["transfer_controls", "duplicate_invoice_policy"]],
    },
    {
        "name": "receipt scope and supplier-risk transfer controls are correct",
        "weight": 3,
        "paths": [["transfer_controls", "receipt_scope_policy"], ["transfer_controls", "risk_policy"]],
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
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
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return sorted([normalize(item) for item in value], key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, dict):
        return {key: normalize(value[key]) for key in sorted(value)}
    return value


def project_records(value: Any, keys: list[str] | None) -> Any:
    if keys is None or not isinstance(value, list):
        return value
    return [{key: item.get(key) for key in keys} if isinstance(item, dict) else item for item in value]


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "usage: evaluator.py <prediction.json>"}))
        return 2
    try:
        pred = load_json(Path(sys.argv[1]))
        gold = load_json(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    except Exception as exc:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": str(exc)}))
        return 1

    total = sum(point["weight"] for point in POINTS)
    earned = 0
    details = []
    for point in POINTS:
        matched = all(
            normalize(project_records(get_path(gold, path), point.get("project")))
            == normalize(project_records(get_path(pred, path), point.get("project")))
            for path in point["paths"]
        )
        earned += point["weight"] if matched else 0
        details.append({"name": point["name"], "matched": matched, "weight": point["weight"]})
    print(
        json.dumps({"score": round(earned / total, 6), "max_score": 1.0, "points": details}, indent=2, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
