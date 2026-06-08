#!/usr/bin/env python3
"""Exact-match evaluator for task_group_007 test_001."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


POINTS = [
    ("SP1_final_decisions", 3, "Correct final_decision for every TEST_PRIORITY_D order."),
    ("SP2_inventory_statuses", 2, "Correct live inventory_status for every order."),
    ("SP3_exception_reasons", 3, "Correct controlled exception reason set for every order."),
    ("SP4_blocking_skus", 2, "Correct live shortage SKU set for every order."),
    ("SP5_shipping_quotes", 1, "Correct shipping cost and service days for every order."),
    ("SP6_summary_counts", 1, "Correct total order count, decision counts, and inventory-status counts."),
    ("SP7_action_sets", 2, "Correct manual-review, backorder, and rejected order id sets."),
    ("SP8_exception_counts", 2, "Correct aggregate exception reason counts."),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def by_order(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("orders", [])
    if not isinstance(rows, list):
        return {}
    result = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("order_id"), str):
            result[row["order_id"]] = row
    return result


def normalized_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return sorted(value)


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


def money(value: Any) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def score(candidate: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    cand_orders = by_order(candidate)
    exp_orders = by_order(expected)
    exp_ids = set(exp_orders)

    details = []

    def add(name: str, weight: int, ok: bool, goal: str) -> None:
        details.append({"id": name, "weight": weight, "matched": bool(ok), "goal": goal})

    add(
        "SP1_final_decisions",
        3,
        set(cand_orders) == exp_ids
        and all(cand_orders[oid].get("final_decision") == exp_orders[oid].get("final_decision") for oid in exp_ids),
        POINTS[0][2],
    )
    add(
        "SP2_inventory_statuses",
        2,
        set(cand_orders) == exp_ids
        and all(
            cand_orders[oid].get("inventory_status") == exp_orders[oid].get("inventory_status") for oid in exp_ids
        ),
        POINTS[1][2],
    )
    add(
        "SP3_exception_reasons",
        3,
        set(cand_orders) == exp_ids
        and all(
            normalized_list(cand_orders[oid].get("exception_reasons"))
            == normalized_list(exp_orders[oid].get("exception_reasons"))
            for oid in exp_ids
        ),
        POINTS[2][2],
    )
    add(
        "SP4_blocking_skus",
        2,
        set(cand_orders) == exp_ids
        and all(
            normalized_list(cand_orders[oid].get("blocking_skus"))
            == normalized_list(exp_orders[oid].get("blocking_skus"))
            for oid in exp_ids
        ),
        POINTS[3][2],
    )
    add(
        "SP5_shipping_quotes",
        1,
        set(cand_orders) == exp_ids
        and all(
            money(cand_orders[oid].get("shipping_cost")) == money(exp_orders[oid].get("shipping_cost"))
            and cand_orders[oid].get("service_days") == exp_orders[oid].get("service_days")
            for oid in exp_ids
        ),
        POINTS[4][2],
    )

    cand_summary = candidate.get("summary", {})
    exp_summary = expected.get("summary", {})
    add(
        "SP6_summary_counts",
        1,
        isinstance(cand_summary, dict)
        and cand_summary.get("order_count") == exp_summary.get("order_count")
        and normalized_counts(cand_summary.get("final_decision_counts"))
        == normalized_counts(exp_summary.get("final_decision_counts"))
        and normalized_counts(cand_summary.get("inventory_status_counts"))
        == normalized_counts(exp_summary.get("inventory_status_counts")),
        POINTS[5][2],
    )
    add(
        "SP7_action_sets",
        2,
        isinstance(cand_summary, dict)
        and normalized_list(cand_summary.get("manual_review_order_ids"))
        == normalized_list(exp_summary.get("manual_review_order_ids"))
        and normalized_list(cand_summary.get("backorder_order_ids"))
        == normalized_list(exp_summary.get("backorder_order_ids"))
        and normalized_list(cand_summary.get("rejected_order_ids"))
        == normalized_list(exp_summary.get("rejected_order_ids")),
        POINTS[6][2],
    )
    add(
        "SP8_exception_counts",
        2,
        isinstance(cand_summary, dict)
        and normalized_counts(cand_summary.get("exception_reason_counts"))
        == normalized_counts(exp_summary.get("exception_reason_counts")),
        POINTS[7][2],
    )

    total_weight = sum(item["weight"] for item in details)
    earned_weight = sum(item["weight"] for item in details if item["matched"])
    return {
        "score": round(earned_weight / total_weight, 6),
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "scoring_points": details,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: evaluate.py <candidate_answer.json>", file=sys.stderr)
        return 2

    script_dir = Path(__file__).resolve().parent
    expected_path = script_dir.parent / "output" / "answer.json"
    candidate_path = Path(sys.argv[1]).resolve()

    try:
        candidate = load_json(candidate_path)
        expected = load_json(expected_path)
    except Exception as exc:
        total_weight = sum(point[1] for point in POINTS)
        print(
            json.dumps({"score": 0.0, "earned_weight": 0, "total_weight": total_weight, "error": str(exc)}, indent=2)
        )
        return 0

    print(json.dumps(score(candidate, expected), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
