#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "id": "SP001",
        "weight": 3,
        "goal": "Correct two key correlation pairs and rounded values.",
        "field": "correlation_summary",
    },
    {
        "id": "SP002",
        "weight": 3,
        "goal": "Correct target sleeve actions.",
        "field": "target_sleeve_actions",
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Correct allocation view rows.",
        "field": "allocation_views",
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "Correct rebalance trigger.",
        "field": "rebalance_trigger",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct portfolio risk concentration flag.",
        "field": "portfolio_risk_concentration_flag",
    },
    {
        "id": "SP006",
        "weight": 1,
        "goal": "Correct next-step enum.",
        "field": "next_step",
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


def normalize_correlation_summary(value):
    if not isinstance(value, list):
        return value
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        pair = item.get("pair")
        if isinstance(pair, list):
            pair = sorted(str(part) for part in pair)
        normalized.append(
            {
                "pair_role": item.get("pair_role"),
                "pair": pair,
                "correlation": round_number(item.get("correlation"), 3),
            }
        )
    return sorted(normalized, key=lambda row: str(row.get("pair_role")))


def normalize_action_rows(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if isinstance(item, dict):
            rows.append(
                {
                    "opportunity_set": item.get("opportunity_set"),
                    "action": item.get("action"),
                }
            )
        else:
            rows.append(item)
    return sorted(rows, key=lambda row: str(row.get("opportunity_set")) if isinstance(row, dict) else str(row))


def normalize_allocation_rows(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if not isinstance(item, dict):
            rows.append(item)
            continue
        rows.append(
            {
                "opportunity_set": item.get("opportunity_set"),
                "prior_view": item.get("prior_view"),
                "signal_score": round_number(item.get("signal_score"), 3),
                "view": item.get("view"),
                "change": item.get("change"),
                "conviction": item.get("conviction"),
                "rationale_code": item.get("rationale_code"),
            }
        )
    return sorted(rows, key=lambda row: str(row.get("opportunity_set")) if isinstance(row, dict) else str(row))


def normalize_field(field, value):
    if field == "correlation_summary":
        return normalize_correlation_summary(value)
    if field == "target_sleeve_actions":
        return normalize_action_rows(value)
    if field == "allocation_views":
        return normalize_allocation_rows(value)
    return value


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(point["weight"] for point in POINTS),
                    "normalized_score": 0.0,
                    "error": "Usage: python eval.py <prediction_json_path>",
                    "details": [],
                },
                indent=2,
            )
        )
        sys.exit(2)

    prediction_path = Path(sys.argv[1])
    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    max_score = sum(point["weight"] for point in POINTS)

    try:
        prediction = load_json(prediction_path)
        answer = load_json(answer_path)
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
        sys.exit(1)

    details = []
    score = 0
    for point in POINTS:
        field = point["field"]
        expected = normalize_field(field, answer.get(field))
        actual = normalize_field(field, prediction.get(field))
        matched = actual == expected
        earned = point["weight"] if matched else 0
        score += earned
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "earned": earned,
                "matched": matched,
                "expected": expected,
                "actual": actual,
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


if __name__ == "__main__":
    main()
