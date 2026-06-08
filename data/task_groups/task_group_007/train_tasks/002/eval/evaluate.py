#!/usr/bin/env python3
"""Exact-match evaluator for task_group_007 train_002."""

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
        "description": "Correct kit targets, build quantities, build dates, and WH_WEST site.",
        "paths": ["kit_targets"],
    },
    {
        "id": "SP002",
        "weight": 2,
        "description": "Correct component demand and WH_WEST effective availability for all BOM components.",
        "paths": [
            "component_plan[].sku",
            "component_plan[].total_required",
            "component_plan[].target_effective_available",
        ],
    },
    {
        "id": "SP003",
        "weight": 3,
        "description": "Correct purchase requisition SKU set, suppliers, quantities, need dates, and extended costs.",
        "paths": ["purchase_requisitions"],
    },
    {
        "id": "SP004",
        "weight": 3,
        "description": "Correct inter-warehouse transfer requests and quantities.",
        "paths": ["transfer_requests"],
    },
    {
        "id": "SP005",
        "weight": 2,
        "description": "Correct timely PO coverage for NW-1005 and exclusion of late or ineligible POs.",
        "paths": [
            "component_plan[NW-1005].timely_po_qty",
            "component_plan[NW-1005].coverage_po_ids",
            "component_plan[NW-1005].final_action",
        ],
    },
    {
        "id": "SP006",
        "weight": 2,
        "description": "Correct overstock exclusion for NW-1039 and excluded component list.",
        "paths": ["excluded_components", "component_plan[NW-1039].final_action"],
    },
    {
        "id": "SP007",
        "weight": 3,
        "description": "Correct component final actions and purchase/transfer quantities across all six SKUs.",
        "paths": [
            "component_plan[].final_action",
            "component_plan[].transfer_qty",
            "component_plan[].purchase_requisition_qty",
            "component_plan[].exclusion_reason",
        ],
    },
    {
        "id": "SP008",
        "weight": 1,
        "description": "Correct aggregate purchase, transfer, PO-covered, and component-count totals.",
        "paths": ["summary"],
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def round_money(value: Any) -> Any:
    if isinstance(value, float):
        return round(value + 0.0, 2)
    return value


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        normalized = [normalize(v) for v in value]
        if all(isinstance(item, dict) for item in normalized):
            return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
        return sorted(normalized) if all(isinstance(item, (str, int, float)) for item in normalized) else normalized
    return round_money(value)


def component_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("component_plan", [])
    if not isinstance(rows, list):
        return {}
    return {str(row.get("sku")): row for row in rows if isinstance(row, dict) and "sku" in row}


def projected_component_fields(payload: dict[str, Any], fields: list[str]) -> list[dict[str, Any]]:
    rows = component_map(payload)
    projected = []
    for sku in sorted(rows):
        row = rows[sku]
        projected.append({"sku": sku, **{field: row.get(field) for field in fields}})
    return projected


def check_point(point_id: str, submission: dict[str, Any], answer: dict[str, Any]) -> bool:
    if point_id == "SP001":
        return normalize(submission.get("kit_targets")) == normalize(answer.get("kit_targets"))
    if point_id == "SP002":
        fields = ["total_required", "target_effective_available"]
        return normalize(projected_component_fields(submission, fields)) == normalize(
            projected_component_fields(answer, fields)
        )
    if point_id == "SP003":
        return normalize(submission.get("purchase_requisitions")) == normalize(answer.get("purchase_requisitions"))
    if point_id == "SP004":
        return normalize(submission.get("transfer_requests")) == normalize(answer.get("transfer_requests"))
    if point_id == "SP005":
        sub = component_map(submission).get("NW-1005", {})
        ans = component_map(answer).get("NW-1005", {})
        fields = ["timely_po_qty", "coverage_po_ids", "final_action", "purchase_requisition_qty", "transfer_qty"]
        return normalize({field: sub.get(field) for field in fields}) == normalize(
            {field: ans.get(field) for field in fields}
        )
    if point_id == "SP006":
        sub = component_map(submission).get("NW-1039", {})
        ans = component_map(answer).get("NW-1039", {})
        return (
            normalize(submission.get("excluded_components")) == normalize(answer.get("excluded_components"))
            and sub.get("final_action") == ans.get("final_action")
            and sub.get("exclusion_reason") == ans.get("exclusion_reason")
        )
    if point_id == "SP007":
        fields = ["final_action", "transfer_qty", "purchase_requisition_qty", "exclusion_reason"]
        return normalize(projected_component_fields(submission, fields)) == normalize(
            projected_component_fields(answer, fields)
        )
    if point_id == "SP008":
        return normalize(submission.get("summary")) == normalize(answer.get("summary"))
    raise ValueError(f"unknown scoring point: {point_id}")


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: evaluate.py <submission.json>"}, indent=2))
        return 2

    submission_path = Path(sys.argv[1])
    try:
        submission = load_json(submission_path)
        answer = load_json(ANSWER_PATH)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"score": 0.0, "error": str(exc), "points": []}, indent=2))
        return 1

    if not isinstance(submission, dict):
        print(json.dumps({"score": 0.0, "error": "submission must be a JSON object", "points": []}, indent=2))
        return 1

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

    print(
        json.dumps(
            {
                "score": round(earned / total_weight, 6),
                "earned_weight": earned,
                "total_weight": total_weight,
                "points": point_results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
