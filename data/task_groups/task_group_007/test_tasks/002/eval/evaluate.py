#!/usr/bin/env python3
"""Exact-match evaluator for task_group_007 test_002."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANSWER_PATH = ROOT / "output" / "answer.json"


SCORING_POINTS = [
    {
        "id": "SP001",
        "weight": 2,
        "description": "Correct campaign target BOMs, target warehouses, build quantities, kit names, and needed-by dates.",
    },
    {
        "id": "SP002",
        "weight": 2,
        "description": "Correct component demand and target effective availability for all component/warehouse rows.",
    },
    {
        "id": "SP003",
        "weight": 3,
        "description": "Correct purchase requisition SKU/warehouse set, suppliers, quantities, need dates, and extended costs.",
    },
    {
        "id": "SP004",
        "weight": 3,
        "description": "Correct inter-warehouse transfer requests and quantities.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "description": "Correct timely PO coverage and late-PO exclusion for eligible component rows.",
    },
    {
        "id": "SP006",
        "weight": 2,
        "description": "Correct excluded component set and controlled exclusion reasons.",
    },
    {
        "id": "SP007",
        "weight": 3,
        "description": "Correct final action plus purchase and transfer quantities for every component/warehouse row.",
    },
    {
        "id": "SP008",
        "weight": 2,
        "description": "Correct aggregate purchase cost, purchase units, transfer units, PO-covered units, and warehouse unit totals.",
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def money(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return value


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        normalized = [normalize(item) for item in value]
        if all(isinstance(item, dict) for item in normalized):
            return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
        if all(isinstance(item, (str, int, float)) for item in normalized):
            return sorted(normalized)
        return normalized
    return money(value)


def component_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("target_warehouse_id")), str(row.get("sku")))


def component_map(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    rows = payload.get("component_plan", [])
    if not isinstance(rows, list):
        return {}
    return {
        component_key(row): row
        for row in rows
        if isinstance(row, dict) and row.get("sku") and row.get("target_warehouse_id")
    }


def projected_components(payload: dict[str, Any], fields: list[str]) -> list[dict[str, Any]]:
    rows = component_map(payload)
    return [
        {
            "target_warehouse_id": warehouse_id,
            "sku": sku,
            **{field: rows[(warehouse_id, sku)].get(field) for field in fields},
        }
        for warehouse_id, sku in sorted(rows)
    ]


def projected_purchase_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("purchase_requisitions", [])
    if not isinstance(rows, list):
        return []
    fields = ["sku", "supplier_id", "warehouse_id", "quantity", "needed_by", "unit_cost", "extended_cost"]
    return [{field: row.get(field) for field in fields} for row in rows if isinstance(row, dict)]


def projected_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        return {}
    fields = [
        "component_count",
        "purchase_requisition_count",
        "total_purchase_units",
        "total_purchase_cost",
        "total_transfer_units",
        "timely_po_covered_units",
        "excluded_component_count",
        "warehouse_purchase_units",
    ]
    return {field: summary.get(field) for field in fields}


def check_point(point_id: str, submission: dict[str, Any], answer: dict[str, Any]) -> bool:
    if point_id == "SP001":
        return normalize(submission.get("campaign_targets")) == normalize(answer.get("campaign_targets"))
    if point_id == "SP002":
        fields = ["bom_id", "total_required", "target_effective_available"]
        return normalize(projected_components(submission, fields)) == normalize(projected_components(answer, fields))
    if point_id == "SP003":
        return normalize(projected_purchase_rows(submission)) == normalize(projected_purchase_rows(answer))
    if point_id == "SP004":
        return normalize(submission.get("transfer_requests")) == normalize(answer.get("transfer_requests"))
    if point_id == "SP005":
        fields = ["timely_po_qty", "coverage_po_ids", "late_po_ids", "final_action", "purchase_requisition_qty"]
        return normalize(projected_components(submission, fields)) == normalize(projected_components(answer, fields))
    if point_id == "SP006":
        fields = ["final_action", "exclusion_reason"]
        return normalize(submission.get("excluded_components")) == normalize(
            answer.get("excluded_components")
        ) and normalize(projected_components(submission, fields)) == normalize(projected_components(answer, fields))
    if point_id == "SP007":
        fields = ["final_action", "transfer_qty", "purchase_requisition_qty", "exclusion_reason"]
        return normalize(projected_components(submission, fields)) == normalize(projected_components(answer, fields))
    if point_id == "SP008":
        return normalize(projected_summary(submission)) == normalize(projected_summary(answer))
    raise ValueError(f"unknown scoring point: {point_id}")


def score(submission: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    total_weight = sum(point["weight"] for point in SCORING_POINTS)
    earned = 0
    point_results = []
    for point in SCORING_POINTS:
        matched = check_point(point["id"], submission, answer)
        if matched:
            earned += point["weight"]
        point_results.append(
            {
                "id": point["id"],
                "weight": point["weight"],
                "matched": matched,
                "description": point["description"],
            }
        )
    return {
        "score": round(earned / total_weight, 6),
        "earned_weight": earned,
        "total_weight": total_weight,
        "points": point_results,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: evaluate.py <submission.json>"}, indent=2))
        return 2

    try:
        submission = load_json(Path(sys.argv[1]))
        answer = load_json(ANSWER_PATH)
    except Exception as exc:  # noqa: BLE001
        total_weight = sum(point["weight"] for point in SCORING_POINTS)
        print(
            json.dumps(
                {"score": 0.0, "earned_weight": 0, "total_weight": total_weight, "error": str(exc), "points": []},
                indent=2,
            )
        )
        return 0

    if not isinstance(submission, dict):
        total_weight = sum(point["weight"] for point in SCORING_POINTS)
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": total_weight,
                    "error": "submission must be a JSON object",
                    "points": [],
                },
                indent=2,
            )
        )
        return 0

    print(json.dumps(score(submission, answer), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
