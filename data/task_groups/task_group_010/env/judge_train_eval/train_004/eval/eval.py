#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "id": "SP001",
        "description": "Correct sell and buy trade package.",
        "weight": 3,
        "path": "rotation.trades",
        "kind": "trade_list",
    },
    {
        "id": "SP002",
        "description": "Correct post-trade HY allocation percentage.",
        "weight": 2,
        "path": "risk_metrics.post_trade_hy_allocation_pct",
        "kind": "number",
        "precision": 2,
    },
    {
        "id": "SP003",
        "description": "Correct post-trade weighted modified duration.",
        "weight": 2,
        "path": "risk_metrics.post_trade_duration_years",
        "kind": "number",
        "precision": 2,
    },
    {
        "id": "SP004",
        "description": "Correct exception flags.",
        "weight": 2,
        "path": "exception_flags",
        "kind": "object",
    },
    {
        "id": "SP005",
        "description": "Correct downgrade and watchlist handling.",
        "weight": 2,
        "path": "watchlist_handling",
        "kind": "object",
    },
    {
        "id": "SP006",
        "description": "Correct risk note code.",
        "weight": 1,
        "path": "risk_note_code",
        "kind": "scalar",
    },
]


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def get_path(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def normalize_number(value, precision):
    try:
        return round(float(value), precision)
    except (TypeError, ValueError):
        return None


def normalize_trade_list(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for row in value:
        if not isinstance(row, dict):
            return None
        action = row.get("action")
        instrument_id = row.get("instrument_id")
        quantity = normalize_number(row.get("quantity_usd_m"), 1)
        if action is None or instrument_id is None or quantity is None:
            return None
        normalized.append(
            {
                "action": str(action),
                "instrument_id": str(instrument_id),
                "quantity_usd_m": quantity,
            }
        )
    action_rank = {"SELL": 0, "BUY": 1}
    return sorted(normalized, key=lambda item: (action_rank.get(item["action"], 9), item["instrument_id"]))


def normalize_obj(value):
    if isinstance(value, dict):
        return {key: normalize_obj(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return sorted((normalize_obj(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, float):
        return round(value, 10)
    return value


def compare(point, expected, predicted):
    exp = get_path(expected, point["path"])
    pred = get_path(predicted, point["path"])
    if point["kind"] == "number":
        exp_norm = normalize_number(exp, point["precision"])
        pred_norm = normalize_number(pred, point["precision"])
    elif point["kind"] == "trade_list":
        exp_norm = normalize_trade_list(exp)
        pred_norm = normalize_trade_list(pred)
    elif point["kind"] == "object":
        exp_norm = normalize_obj(exp)
        pred_norm = normalize_obj(pred)
    else:
        exp_norm = exp
        pred_norm = pred
    return exp_norm == pred_norm, exp_norm, pred_norm


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(p["weight"] for p in POINTS),
                    "normalized_score": 0,
                    "error": "Usage: eval.py <prediction_json_path>",
                }
            )
        )
        return 2

    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        expected = load_json(answer_path)
        predicted = load_json(sys.argv[1])
    except Exception as exc:
        max_score = sum(point["weight"] for point in POINTS)
        print(json.dumps({"score": 0, "max_score": max_score, "normalized_score": 0, "error": str(exc)}, indent=2))
        return 1

    details = []
    score = 0
    for point in POINTS:
        matched, expected_value, predicted_value = compare(point, expected, predicted)
        earned = point["weight"] if matched else 0
        score += earned
        details.append(
            {
                "id": point["id"],
                "description": point["description"],
                "weight": point["weight"],
                "earned": earned,
                "matched": matched,
                "expected": expected_value,
                "predicted": predicted_value,
            }
        )

    max_score = sum(point["weight"] for point in POINTS)
    result = {
        "score": score,
        "max_score": max_score,
        "normalized_score": round(score / max_score, 6),
        "points": details,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
