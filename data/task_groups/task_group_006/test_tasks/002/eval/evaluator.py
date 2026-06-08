#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


POINTS = [
    (
        "package identity, cutoff date, and target invoice set",
        3,
        [["task_id"], ["package_id"], ["as_of_date"], ["target_invoice_ids"]],
        None,
    ),
    (
        "invoice supplier, program, PO, and AP status fields",
        3,
        [["invoice_release_lines"]],
        [
            "invoice_id",
            "supplier_id",
            "supplier_name",
            "program_id",
            "po_id",
            "po_status",
            "invoice_status",
            "hold_code",
        ],
    ),
    (
        "receipt cutoff matching and quantity reconciliation",
        2,
        [["invoice_release_lines"]],
        [
            "invoice_id",
            "receipt_ids_as_of",
            "excluded_receipt_ids",
            "receipt_cutoff_status",
            "exception_codes",
            "quantity_billed",
            "quantity_received_as_of",
            "quantity_variance_as_of",
        ],
    ),
    (
        "payment linkage, statuses, dates, and bank actions",
        2,
        [["invoice_release_lines"]],
        ["invoice_id", "payment_id", "payment_status", "payment_scheduled_date", "payment_amount", "bank_action"],
    ),
    (
        "release and hold decisions, queues, and package totals",
        3,
        [
            ["invoice_release_lines"],
            ["release_queue"],
            ["hold_queue"],
            ["bank_action_summary", "total_release_amount"],
            ["bank_action_summary", "total_hold_amount"],
            ["bank_action_summary", "total_exception_payment_amount"],
        ],
        ["invoice_id", "release_decision", "invoice_total", "release_amount", "hold_amount"],
    ),
    ("supplier release summary", 2, [["supplier_release_summary"]], None),
    ("program summary", 2, [["program_summary"]], None),
    (
        "payment ID buckets and source precedence",
        1,
        [
            ["bank_action_summary", "release_payment_ids"],
            ["bank_action_summary", "blocked_payment_ids"],
            ["bank_action_summary", "suppress_payment_ids"],
            ["bank_action_summary", "recall_or_stop_payment_ids"],
            ["source_precedence"],
        ],
        None,
    ),
]


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def at(obj: Any, path: list[str]) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def norm(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, list):
        return sorted((norm(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, dict):
        return {key: norm(value[key]) for key in sorted(value)}
    if isinstance(value, str):
        return value.strip()
    return value


def project(value: Any, keys: list[str] | None) -> Any:
    if keys is None or not isinstance(value, list):
        return value
    return [{key: row.get(key) for key in keys} if isinstance(row, dict) else row for row in value]


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "usage: evaluator.py <prediction.json>"}))
        return 2
    try:
        pred = load(Path(sys.argv[1]))
        gold = load(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    except Exception as exc:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": str(exc)}))
        return 1

    total = sum(weight for _, weight, _, _ in POINTS)
    earned = 0
    details = []
    for name, weight, paths, keys in POINTS:
        matched = True
        for path in paths:
            point_keys = keys if path == ["invoice_release_lines"] else None
            if norm(project(at(pred, path), point_keys)) != norm(project(at(gold, path), point_keys)):
                matched = False
                break
        if matched:
            earned += weight
        details.append({"name": name, "matched": matched, "weight": weight})
    print(
        json.dumps({"score": round(earned / total, 6), "max_score": 1.0, "points": details}, indent=2, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
