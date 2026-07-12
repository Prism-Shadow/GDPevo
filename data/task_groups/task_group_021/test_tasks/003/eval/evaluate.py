#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
GOLD_PATH = TASK_DIR / "output" / "answer.json"

POINTS = [
    {
        "id": "SP001",
        "goal": "Correct wave identifier and effective event count.",
        "weight": 2,
        "fields": ["wave_id", "effective_event_count"],
    },
    {
        "id": "SP002",
        "goal": "Correct invalid event IDs and their controlled issue types.",
        "weight": 2,
        "fields": ["invalid_event_ids", "invalid_event_issue_types"],
    },
    {
        "id": "SP003",
        "goal": "Correct lifecycle reconstruction audit plus duplicate and amendment outputs.",
        "weight": 3,
        "fields": ["duplicate_business_key_count", "amended_event_ids_used", "decision_audit"],
    },
    {
        "id": "SP004",
        "goal": "Correct total corrected shipment cost in USD cents.",
        "weight": 3,
        "fields": ["corrected_total_usd"],
    },
    {
        "id": "SP005",
        "goal": "Correct corrected USD totals for each controlled cost type.",
        "weight": 3,
        "fields": ["cost_type_totals_usd"],
    },
    {
        "id": "SP006",
        "goal": "Correct top lane by corrected cost and lane amount.",
        "weight": 2,
        "fields": ["top_lane_by_cost"],
    },
    {
        "id": "SP007",
        "goal": "Correct effective source-unit counts after exclusions.",
        "weight": 2,
        "fields": ["unit_correction_counts"],
    },
    {
        "id": "SP008",
        "goal": "Correct controlled issue-type count summary.",
        "weight": 3,
        "fields": ["issue_type_counts"],
    },
]

MONEY_FIELDS = {
    ("corrected_total_usd",),
    ("cost_type_totals_usd", "freight"),
    ("cost_type_totals_usd", "accessorial"),
    ("cost_type_totals_usd", "tax_fee"),
    ("cost_type_totals_usd", "claim"),
    ("top_lane_by_cost", "amount_usd"),
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cents(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize_value(value, path=()):
    if path in MONEY_FIELDS:
        return cents(value)
    if isinstance(value, dict):
        return {key: normalize_value(val, path + (key,)) for key, val in value.items()}
    if isinstance(value, list):
        return [normalize_value(item, path + ("[]",)) for item in value]
    return value


def project(obj, fields):
    return {field: normalize_value(obj.get(field), (field,)) for field in fields}


def main() -> int:
    prediction_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    prediction_path = Path(prediction_arg) if prediction_arg else GOLD_PATH
    if not prediction_path.is_absolute():
        prediction_path = Path.cwd() / prediction_path

    gold = load_json(GOLD_PATH)
    try:
        pred = load_json(prediction_path)
    except Exception as exc:
        total_weight = sum(point["weight"] for point in POINTS)
        print(json.dumps({
            "score": 0,
            "max_score": total_weight,
            "normalized_score": 0.0,
            "error": f"Could not parse prediction JSON: {exc}",
            "points": []
        }, indent=2))
        return 0

    scored = []
    score = 0
    for point in POINTS:
        expected = project(gold, point["fields"])
        actual = project(pred, point["fields"])
        passed = actual == expected
        if passed:
            score += point["weight"]
        scored.append({
            "id": point["id"],
            "goal": point["goal"],
            "weight": point["weight"],
            "passed": passed,
            "expected": expected,
            "actual": actual,
        })

    total_weight = sum(point["weight"] for point in POINTS)
    print(json.dumps({
        "score": score,
        "max_score": total_weight,
        "normalized_score": round(score / total_weight, 6),
        "points": scored,
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
