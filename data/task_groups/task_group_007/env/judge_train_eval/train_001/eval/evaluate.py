#!/usr/bin/env python3
"""Exact-match evaluator for task_group_007 train_001."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCORING_POINTS = [
    ("SP001_order_set_and_count", 1),
    ("SP002_inventory_statuses_and_shortages", 3),
    ("SP003_inactive_and_low_stock_sku_sets", 2),
    ("SP004_customer_exceptions", 2),
    ("SP005_final_decisions", 3),
    ("SP006_next_actions", 2),
    ("SP007_shipping_quotes", 2),
    ("SP008_summary_rollups", 2),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def round_money(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return round(float(value) + 0.0, 2)
    return value


def sorted_strings(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return sorted(value)


def normalize_records(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = payload.get("records")
    if not isinstance(records, list):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        order_id = record.get("order_id")
        if not isinstance(order_id, str):
            continue
        quote = record.get("shipping_quote") if isinstance(record.get("shipping_quote"), dict) else {}
        normalized[order_id] = {
            "inventory_status": record.get("inventory_status"),
            "customer_exception": record.get("customer_exception"),
            "final_decision": record.get("final_decision"),
            "next_action": record.get("next_action"),
            "shortage_skus": sorted_strings(record.get("shortage_skus")),
            "inactive_skus": sorted_strings(record.get("inactive_skus")),
            "low_stock_skus": sorted_strings(record.get("low_stock_skus")),
            "shipping_quote": {
                "zone_distance": quote.get("zone_distance"),
                "service_days": quote.get("service_days"),
                "total_cost_usd": round_money(quote.get("total_cost_usd")),
            },
        }
    return normalized


def normalize_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return {}
    decision_counts = summary.get("decision_counts")
    if not isinstance(decision_counts, dict):
        decision_counts = {}
    return {
        "order_count": summary.get("order_count"),
        "decision_counts": {
            key: decision_counts.get(key)
            for key in ["ship_now", "delayed_release", "manual_review", "backorder", "reject_hold"]
        },
        "total_shipping_cost_usd": round_money(summary.get("total_shipping_cost_usd")),
        "blocked_order_ids": sorted_strings(summary.get("blocked_order_ids")),
        "manual_review_order_ids": sorted_strings(summary.get("manual_review_order_ids")),
        "backorder_order_ids": sorted_strings(summary.get("backorder_order_ids")),
        "inactive_sku_order_ids": sorted_strings(summary.get("inactive_sku_order_ids")),
    }


def score(candidate: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    candidate_records = normalize_records(candidate)
    expected_records = normalize_records(expected)
    candidate_summary = normalize_summary(candidate)
    expected_summary = normalize_summary(expected)
    expected_order_ids = sorted(expected_records)

    checks: dict[str, bool] = {}
    checks["SP001_order_set_and_count"] = (
        candidate.get("wave_id") == expected.get("wave_id")
        and sorted(candidate_records) == expected_order_ids
        and candidate_summary.get("order_count") == expected_summary.get("order_count")
    )

    checks["SP002_inventory_statuses_and_shortages"] = all(
        candidate_records.get(order_id, {}).get("inventory_status") == expected_records[order_id]["inventory_status"]
        and candidate_records.get(order_id, {}).get("shortage_skus") == expected_records[order_id]["shortage_skus"]
        for order_id in expected_order_ids
    )

    checks["SP003_inactive_and_low_stock_sku_sets"] = all(
        candidate_records.get(order_id, {}).get("inactive_skus") == expected_records[order_id]["inactive_skus"]
        and candidate_records.get(order_id, {}).get("low_stock_skus") == expected_records[order_id]["low_stock_skus"]
        for order_id in expected_order_ids
    )

    checks["SP004_customer_exceptions"] = all(
        candidate_records.get(order_id, {}).get("customer_exception")
        == expected_records[order_id]["customer_exception"]
        for order_id in expected_order_ids
    )

    checks["SP005_final_decisions"] = all(
        candidate_records.get(order_id, {}).get("final_decision") == expected_records[order_id]["final_decision"]
        for order_id in expected_order_ids
    )

    checks["SP006_next_actions"] = all(
        candidate_records.get(order_id, {}).get("next_action") == expected_records[order_id]["next_action"]
        for order_id in expected_order_ids
    )

    checks["SP007_shipping_quotes"] = all(
        candidate_records.get(order_id, {}).get("shipping_quote") == expected_records[order_id]["shipping_quote"]
        for order_id in expected_order_ids
    )

    checks["SP008_summary_rollups"] = candidate_summary == expected_summary

    total_weight = sum(weight for _, weight in SCORING_POINTS)
    earned_weight = sum(weight for name, weight in SCORING_POINTS if checks[name])
    return {
        "score": earned_weight / total_weight,
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "scoring_points": [
            {
                "id": name,
                "weight": weight,
                "matched": checks[name],
                "normalized_weight": weight / total_weight,
            }
            for name, weight in SCORING_POINTS
        ],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: evaluate.py <candidate_answer.json>", file=sys.stderr)
        return 2
    candidate_path = Path(sys.argv[1])
    expected_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        candidate = load_json(candidate_path)
        expected = load_json(expected_path)
    except Exception as exc:
        total_weight = sum(weight for _, weight in SCORING_POINTS)
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": total_weight,
                    "error": f"Could not load JSON: {exc}",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not isinstance(candidate, dict):
        total_weight = sum(weight for _, weight in SCORING_POINTS)
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": total_weight,
                    "error": "Candidate answer must be a JSON object.",
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
