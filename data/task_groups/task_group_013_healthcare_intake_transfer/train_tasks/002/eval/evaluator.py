#!/usr/bin/env python3
import json
import sys
from pathlib import Path


SCORING = [
    ("task_id", 1),
    ("transfer_decisions", 3),
    ("missing_packet_items", 3),
    ("stale_items", 2),
    ("start_compatibility", 2),
    ("route_owners", 2),
    ("summary_and_flags", 1),
]


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sorted_list(value):
    if not isinstance(value, list):
        return value
    return sorted(value)


def transfer_map(answer):
    transfers = answer.get("transfers")
    if not isinstance(transfers, list):
        return {}
    result = {}
    for row in transfers:
        if isinstance(row, dict) and isinstance(row.get("transfer_id"), str):
            result[row["transfer_id"]] = row
    return result


def compare_transfer_field(prediction, gold, field):
    pred_transfers = transfer_map(prediction)
    gold_transfers = transfer_map(gold)
    if set(pred_transfers) != set(gold_transfers):
        return False
    for transfer_id, gold_row in gold_transfers.items():
        pred_row = pred_transfers[transfer_id]
        pred_value = pred_row.get(field)
        gold_value = gold_row.get(field)
        if isinstance(gold_value, list):
            pred_value = sorted_list(pred_value)
            gold_value = sorted_list(gold_value)
        if pred_value != gold_value:
            return False
    return True


def compare_summary_and_flags(prediction, gold):
    if prediction.get("accepted_count") != gold.get("accepted_count"):
        return False
    for field in ("authorization_problem_transfers", "confidentiality_problem_transfers"):
        if sorted_list(prediction.get(field)) != sorted_list(gold.get(field)):
            return False
    pred_transfers = transfer_map(prediction)
    gold_transfers = transfer_map(gold)
    if set(pred_transfers) != set(gold_transfers):
        return False
    for transfer_id, gold_row in gold_transfers.items():
        pred_row = pred_transfers[transfer_id]
        for field in ("authorization_valid", "confidentiality_valid"):
            if pred_row.get(field) != gold_row.get(field):
                return False
    return True


def score(prediction, gold):
    checks = {
        "task_id": prediction.get("task_id") == gold.get("task_id"),
        "transfer_decisions": compare_transfer_field(prediction, gold, "decision"),
        "missing_packet_items": compare_transfer_field(prediction, gold, "missing_packet_items"),
        "stale_items": compare_transfer_field(prediction, gold, "stale_items"),
        "start_compatibility": compare_transfer_field(prediction, gold, "start_compatibility"),
        "route_owners": compare_transfer_field(prediction, gold, "route_owner"),
        "summary_and_flags": compare_summary_and_flags(prediction, gold),
    }
    total = sum(weight for _, weight in SCORING)
    earned = sum(weight for name, weight in SCORING if checks[name])
    return {
        "score": earned,
        "max_score": total,
        "passed": earned == total,
        "details": [
            {
                "name": name,
                "points": weight if checks[name] else 0,
                "max_points": weight,
                "matched": checks[name],
            }
            for name, weight in SCORING
        ],
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: evaluator.py PREDICTION_JSON GOLD_JSON", file=sys.stderr)
        return 2
    prediction = load_json(sys.argv[1])
    gold = load_json(sys.argv[2])
    result = score(prediction, gold)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
