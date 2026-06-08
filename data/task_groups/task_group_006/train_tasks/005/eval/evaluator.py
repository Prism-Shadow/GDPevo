#!/usr/bin/env python3
"""Exact-match evaluator for task_group_006 train_005."""

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
        "name": "invoice release decisions and primary reasons are correct",
        "weight": 3,
        "paths": [["release_decisions"]],
        "project": ["invoice_id", "po_id", "decision", "primary_reason"],
    },
    {
        "name": "in-scope and excluded receipt IDs are correct",
        "weight": 2,
        "paths": [["release_decisions"]],
        "project": ["invoice_id", "receipt_ids_in_scope", "excluded_same_po_receipt_ids"],
    },
    {
        "name": "per-invoice chargeback and net release amounts are correct",
        "weight": 2,
        "paths": [["release_decisions"]],
        "project": [
            "invoice_id",
            "invoice_total",
            "approved_chargeback_amount",
            "pending_chargeback_amount",
            "net_release_amount",
        ],
    },
    {
        "name": "release and hold invoice sets plus financial totals are correct",
        "weight": 3,
        "paths": [
            ["summary", "release_invoice_ids"],
            ["summary", "hold_invoice_ids"],
            ["summary", "approved_chargeback_total"],
            ["summary", "pending_chargeback_total"],
            ["summary", "net_release_total"],
        ],
    },
    {
        "name": "receiving exceptions and chargeback statuses are correct",
        "weight": 2,
        "paths": [["receiving_exceptions"]],
    },
    {
        "name": "source precedence classifications are correct",
        "weight": 2,
        "paths": [["summary", "authoritative_sources"], ["summary", "supporting_only_sources"]],
    },
    {
        "name": "follow-up action set is correct",
        "weight": 1,
        "paths": [["summary", "followup_actions"]],
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


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "usage: evaluator.py <prediction.json>"}))
        return 2

    pred_path = Path(sys.argv[1])
    gold_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"

    try:
        pred = load_json(pred_path)
        gold = load_json(gold_path)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": str(exc)}))
        return 1

    total_weight = sum(point["weight"] for point in POINTS)
    earned = 0
    details = []

    for point in POINTS:
        matched = True
        for path in point["paths"]:
            gold_value = project_records(get_path(gold, path), point.get("project"))
            pred_value = project_records(get_path(pred, path), point.get("project"))
            if normalize(gold_value) != normalize(pred_value):
                matched = False
                break
        if matched:
            earned += point["weight"]
        details.append({"name": point["name"], "matched": matched, "weight": point["weight"]})

    score = round(earned / total_weight, 6)
    print(json.dumps({"score": score, "max_score": 1.0, "points": details}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
