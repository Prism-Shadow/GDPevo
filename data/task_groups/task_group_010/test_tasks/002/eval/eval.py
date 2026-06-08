#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "id": "SP001",
        "weight": 1,
        "goal": "Correct review window and expanded index universe.",
        "fields": ["review_window", "index_set"],
    },
    {
        "id": "SP002",
        "weight": 2,
        "goal": "Correct expanded pair correlation grid with three-decimal values.",
        "field": "pair_calculations",
    },
    {
        "id": "SP003",
        "weight": 3,
        "goal": "Correct highest and lowest pairs with rounded correlations.",
        "field": "extreme_pairs",
    },
    {
        "id": "SP004",
        "weight": 3,
        "goal": "Correct China/Asia dependence and Latin America diversification flags.",
        "field": "concentration_flags",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct diversification action set.",
        "field": "diversification_actions",
    },
    {
        "id": "SP006",
        "weight": 2,
        "goal": "Correct hedging next-step enum.",
        "field": "hedging_next_step",
    },
    {
        "id": "SP007",
        "weight": 1,
        "goal": "Correct concentration threshold boolean.",
        "field": "concentration_threshold_breached",
    },
]


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def round_number(value, digits=3):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), digits)
    return value


def normalize_pair_object(value):
    if not isinstance(value, dict):
        return value
    pair = value.get("pair_id")
    if isinstance(pair, list):
        pair = sorted(str(part) for part in pair)
    return {
        "pair_id": pair,
        "correlation": round_number(value.get("correlation"), 3),
    }


def normalize_pair_list(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        rows.append(normalize_pair_object(item))
    return sorted(rows, key=lambda row: tuple(row.get("pair_id", [])) if isinstance(row, dict) else str(row))


def normalize_extreme_pairs(value):
    if not isinstance(value, dict):
        return value
    return {
        "highest_positive": normalize_pair_object(value.get("highest_positive")),
        "lowest": normalize_pair_object(value.get("lowest")),
    }


def normalize_action_rows(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if isinstance(item, dict):
            rows.append(
                {
                    "sleeve": item.get("sleeve"),
                    "action": item.get("action"),
                    "target_index_id": item.get("target_index_id"),
                }
            )
        else:
            rows.append(item)
    return sorted(rows, key=lambda row: str(row.get("sleeve")) if isinstance(row, dict) else str(row))


def normalize_value(field, value):
    if field == "pair_calculations":
        return normalize_pair_list(value)
    if field == "extreme_pairs":
        return normalize_extreme_pairs(value)
    if field == "diversification_actions":
        return normalize_action_rows(value)
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, list):
        return [normalize_value(field, item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_value(field, value[key]) for key in sorted(value)}
    return value


def point_value(document, point):
    if "fields" in point:
        return {field: document.get(field) for field in point["fields"]}
    return document.get(point["field"])


def main():
    max_score = sum(point["weight"] for point in POINTS)
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": max_score,
                    "normalized_score": 0.0,
                    "error": "Usage: python eval.py <prediction_json_path>",
                    "details": [],
                },
                indent=2,
            )
        )
        return 2

    answer_path = Path(__file__).resolve().parent.parent / "output" / "answer.json"
    try:
        expected = load_json(answer_path)
        predicted = load_json(sys.argv[1])
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": max_score,
                    "normalized_score": 0.0,
                    "error": str(exc),
                    "details": [],
                },
                indent=2,
            )
        )
        return 1

    score = 0
    details = []
    for point in POINTS:
        if "fields" in point:
            expected_value = {field: normalize_value(field, expected.get(field)) for field in point["fields"]}
            actual_value = {field: normalize_value(field, predicted.get(field)) for field in point["fields"]}
        else:
            field = point["field"]
            expected_value = normalize_value(field, point_value(expected, point))
            actual_value = normalize_value(field, point_value(predicted, point))
        matched = actual_value == expected_value
        earned = point["weight"] if matched else 0
        score += earned
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "earned": earned,
                "matched": matched,
                "expected": expected_value,
                "actual": actual_value,
            }
        )

    print(
        json.dumps(
            {
                "score": score,
                "max_score": max_score,
                "normalized_score": round(score / max_score, 6),
                "details": details,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
