#!/usr/bin/env python3
"""Exact-match evaluator for task_group_007 test_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


POINTS = [
    ("SP1_release_decisions", 3, "Correct release_decision for every TEST_QUALITY_E order."),
    ("SP2_inventory_blockers", 2, "Correct inventory_status and blocked_skus for every order."),
    ("SP3_reason_codes", 3, "Correct controlled reason code set for every order."),
    ("SP4_quality_hold_mapping", 2, "Correct per-order quality-hold supplier mapping."),
    ("SP5_active_severe_incidents", 2, "Correct per-order active severe incident IDs and risk supplier IDs."),
    (
        "SP6_risk_supplier_rollup",
        3,
        "Correct risk supplier rollup with risk type, affected SKUs, incident IDs, and orders.",
    ),
    ("SP7_next_actions", 1, "Correct next action for every order."),
    ("SP8_summary", 1, "Correct decision counts, inventory counts, order-id sets, and risk totals."),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): normalize(val) for key, val in sorted(value.items())}
    if isinstance(value, list):
        items = [normalize(item) for item in value]
        if all(isinstance(item, dict) for item in items):
            return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
        if all(isinstance(item, (str, int, float, bool)) or item is None for item in items):
            return sorted(items)
        return items
    return value


def by_order(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("orders", [])
    if not isinstance(rows, list):
        return {}
    return {row["order_id"]: row for row in rows if isinstance(row, dict) and isinstance(row.get("order_id"), str)}


def orders_match(candidate: dict[str, Any], expected: dict[str, Any], fields: list[str]) -> bool:
    cand_orders = by_order(candidate)
    exp_orders = by_order(expected)
    if set(cand_orders) != set(exp_orders):
        return False
    for order_id, exp in exp_orders.items():
        cand = cand_orders[order_id]
        if normalize({field: cand.get(field) for field in fields}) != normalize(
            {field: exp.get(field) for field in fields}
        ):
            return False
    return True


def normalized_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for key, raw in value.items():
        try:
            count = int(raw)
        except (TypeError, ValueError):
            return {}
        if count != 0:
            out[str(key)] = count
    return dict(sorted(out.items()))


def summary_projection(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        return {}
    return {
        "order_count": summary.get("order_count"),
        "release_decision_counts": normalized_counts(summary.get("release_decision_counts")),
        "inventory_status_counts": normalized_counts(summary.get("inventory_status_counts")),
        "release_order_ids": normalize(summary.get("release_order_ids")),
        "manual_review_order_ids": normalize(summary.get("manual_review_order_ids")),
        "backorder_order_ids": normalize(summary.get("backorder_order_ids")),
        "risk_supplier_count": summary.get("risk_supplier_count"),
        "active_severe_incident_count": summary.get("active_severe_incident_count"),
    }


def check_point(point_id: str, candidate: dict[str, Any], expected: dict[str, Any]) -> bool:
    if point_id == "SP1_release_decisions":
        return orders_match(candidate, expected, ["release_decision"])
    if point_id == "SP2_inventory_blockers":
        return orders_match(candidate, expected, ["inventory_status", "blocked_skus"])
    if point_id == "SP3_reason_codes":
        return orders_match(candidate, expected, ["reason_codes"])
    if point_id == "SP4_quality_hold_mapping":
        return orders_match(candidate, expected, ["quality_hold_suppliers"])
    if point_id == "SP5_active_severe_incidents":
        return orders_match(candidate, expected, ["active_severe_incident_ids", "risk_suppliers"])
    if point_id == "SP6_risk_supplier_rollup":
        return normalize(candidate.get("risk_suppliers")) == normalize(expected.get("risk_suppliers"))
    if point_id == "SP7_next_actions":
        return orders_match(candidate, expected, ["next_action"])
    if point_id == "SP8_summary":
        return normalize(summary_projection(candidate)) == normalize(summary_projection(expected))
    raise ValueError(f"unknown scoring point: {point_id}")


def score(candidate: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    details = []
    earned = 0
    for point_id, weight, goal in POINTS:
        matched = check_point(point_id, candidate, expected)
        if matched:
            earned += weight
        details.append({"id": point_id, "weight": weight, "matched": matched, "goal": goal})
    total_weight = sum(weight for _, weight, _ in POINTS)
    return {
        "score": round(earned / total_weight, 6),
        "earned_weight": earned,
        "total_weight": total_weight,
        "scoring_points": details,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: evaluate.py <candidate_answer.json>", file=sys.stderr)
        return 2
    expected_path = Path(__file__).resolve().parent.parent / "output" / "answer.json"
    total_weight = sum(weight for _, weight, _ in POINTS)
    try:
        candidate = load_json(Path(sys.argv[1]).resolve())
        expected = load_json(expected_path)
        if not isinstance(candidate, dict):
            raise TypeError("candidate answer must be a JSON object")
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": total_weight,
                    "error": str(exc),
                    "scoring_points": [],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(score(candidate, expected), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
