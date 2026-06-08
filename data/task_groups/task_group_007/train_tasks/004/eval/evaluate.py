#!/usr/bin/env python3
"""Exact-match evaluator for train_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


LINE_KEYS = ("order_id", "line_id")


def load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def by_line(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (str(row.get("order_id", "")), int(row.get("line_id", -1))))


def by_order(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: str(row.get("order_id", "")))


def line_subset(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    return by_line([{key: row.get(key) for key in keys} for row in rows])


def transfer_rows(answer: dict[str, Any]) -> list[dict[str, Any]]:
    return by_line(answer.get("transfer_requests", []))


def backorder_rows(answer: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in answer.get("line_actions", []):
        if row.get("backorder_quantity", 0) > 0:
            rows.append(
                {
                    "order_id": row.get("order_id"),
                    "line_id": row.get("line_id"),
                    "sku": row.get("sku"),
                    "backorder_quantity": row.get("backorder_quantity"),
                    "primary_reason": row.get("primary_reason"),
                }
            )
    return by_line(rows)


def manual_review_rows(answer: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in answer.get("line_actions", []):
        if row.get("action") == "manual_review":
            rows.append(
                {
                    "order_id": row.get("order_id"),
                    "line_id": row.get("line_id"),
                    "primary_reason": row.get("primary_reason"),
                }
            )
    return by_line(rows)


def ship_rows(answer: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in answer.get("line_actions", []):
        if row.get("action") == "ship":
            rows.append(
                {
                    "order_id": row.get("order_id"),
                    "line_id": row.get("line_id"),
                    "sku": row.get("sku"),
                    "ship_quantity": row.get("ship_quantity"),
                }
            )
    return by_line(rows)


def order_control(answer: dict[str, Any]) -> dict[str, Any]:
    return {
        "blocked_orders": sorted(answer.get("blocked_orders", [])),
        "order_rollup": by_order(answer.get("order_rollup", [])),
    }


def score_point(name: str, weight: int, got: Any, expected: Any) -> dict[str, Any]:
    matched = got == expected
    return {"name": name, "weight": weight, "matched": matched}


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: evaluate.py <candidate_answer.json> <standard_answer.json>", file=sys.stderr)
        return 2

    try:
        candidate = load_json(sys.argv[1])
        expected = load_json(sys.argv[2])
    except Exception as exc:  # noqa: BLE001
        result = {
            "score": 0.0,
            "earned_weight": 0,
            "total_weight": 17,
            "error": f"Could not parse input JSON: {exc}",
            "points": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    points = [
        score_point(
            "SP1_wave_and_line_action_set",
            2,
            {
                "wave_id": candidate.get("wave_id"),
                "lines": line_subset(candidate.get("line_actions", []), ("order_id", "line_id", "sku", "action")),
            },
            {
                "wave_id": expected.get("wave_id"),
                "lines": line_subset(expected.get("line_actions", []), ("order_id", "line_id", "sku", "action")),
            },
        ),
        score_point("SP2_manual_review_reason_set", 3, manual_review_rows(candidate), manual_review_rows(expected)),
        score_point("SP3_direct_ship_quantities", 2, ship_rows(candidate), ship_rows(expected)),
        score_point("SP4_transfer_request_set", 3, transfer_rows(candidate), transfer_rows(expected)),
        score_point("SP5_backorder_quantities", 2, backorder_rows(candidate), backorder_rows(expected)),
        score_point(
            "SP6_requested_effective_available_values",
            2,
            line_subset(candidate.get("line_actions", []), ("order_id", "line_id", "requested_effective_available")),
            line_subset(expected.get("line_actions", []), ("order_id", "line_id", "requested_effective_available")),
        ),
        score_point("SP7_order_rollup_and_blocked_orders", 2, order_control(candidate), order_control(expected)),
        score_point("SP8_summary_counts", 1, candidate.get("summary"), expected.get("summary")),
    ]

    total = sum(point["weight"] for point in points)
    earned = sum(point["weight"] for point in points if point["matched"])
    result = {
        "score": round(earned / total, 6),
        "earned_weight": earned,
        "total_weight": total,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
