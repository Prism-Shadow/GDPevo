#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    ("SP001", 2, "adverse-rated loan count and balance"),
    ("SP002", 3, "risk classes for watch-list loans"),
    ("SP003", 3, "stressed DSCR breach set"),
    ("SP004", 2, "largest problem exposure and action"),
    ("SP005", 2, "underwater projected-loss classification"),
    ("SP006", 2, "payment-status by risk-rating severe bucket counts"),
    ("SP007", 1, "monitoring cadence"),
]


def load_json(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def money(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def ratio2(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def sorted_strings(values):
    if not isinstance(values, list):
        return None
    return sorted(str(v) for v in values)


def risk_classes(answer):
    rows = answer.get("watch_list_summary", {}).get("risk_classes")
    if not isinstance(rows, list):
        return None
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        normalized.append(
            {
                "loan_id": str(row.get("loan_id")),
                "risk_class": str(row.get("risk_class")),
                "factor_score": as_int(row.get("factor_score")),
            }
        )
    return sorted(normalized, key=lambda row: row["loan_id"])


def stress_results(answer):
    rows = answer.get("stress_results", {}).get("results")
    if not isinstance(rows, list):
        return None
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        normalized.append(
            {
                "loan_id": str(row.get("loan_id")),
                "base_dscr": ratio2(row.get("base_dscr")),
                "stressed_dscr": ratio2(row.get("stressed_dscr")),
                "breaches_threshold": bool(row.get("breaches_threshold")),
            }
        )
    return sorted(normalized, key=lambda row: row["loan_id"])


def workout_queue(answer):
    rows = answer.get("workout_queue")
    if not isinstance(rows, list):
        return None
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        normalized.append(
            {
                "loan_id": str(row.get("loan_id")),
                "exposure": money(row.get("exposure")),
                "risk_class": str(row.get("risk_class")),
                "payment_status": str(row.get("payment_status")),
                "recommended_action": str(row.get("recommended_action")),
                "projected_loss": bool(row.get("projected_loss")),
            }
        )
    return sorted(normalized, key=lambda row: (-row["exposure"], row["loan_id"]))


def severe_counts(answer):
    rows = answer.get("severe_bucket_counts")
    if not isinstance(rows, list):
        return None
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        normalized.append(
            {
                "current_rating": as_int(row.get("current_rating")),
                "payment_status": str(row.get("payment_status")),
                "loan_count": as_int(row.get("loan_count")),
                "exposure": money(row.get("exposure")),
            }
        )
    return sorted(normalized, key=lambda row: (row["current_rating"], row["payment_status"]))


def top_problem(answer):
    queue = workout_queue(answer)
    return None if not queue else queue[0]


def projected_loss_item(answer):
    queue = workout_queue(answer)
    if queue is None:
        return None
    return sorted([row for row in queue if row["projected_loss"]], key=lambda row: row["loan_id"])


def score_prediction(prediction, expected):
    checks = {
        "SP001": (
            prediction.get("branch_id") == expected.get("branch_id")
            and as_int(prediction.get("watch_list_summary", {}).get("adverse_rating_min"))
            == expected["watch_list_summary"]["adverse_rating_min"]
            and as_int(prediction.get("watch_list_summary", {}).get("adverse_loan_count"))
            == expected["watch_list_summary"]["adverse_loan_count"]
            and money(prediction.get("watch_list_summary", {}).get("adverse_balance"))
            == money(expected["watch_list_summary"]["adverse_balance"])
        ),
        "SP002": risk_classes(prediction) == risk_classes(expected),
        "SP003": (
            prediction.get("stress_results", {}).get("shock_label") == expected["stress_results"]["shock_label"]
            and ratio2(prediction.get("stress_results", {}).get("breach_threshold"))
            == ratio2(expected["stress_results"]["breach_threshold"])
            and stress_results(prediction) == stress_results(expected)
            and sorted_strings(prediction.get("stress_results", {}).get("breach_loan_ids"))
            == sorted_strings(expected["stress_results"]["breach_loan_ids"])
        ),
        "SP004": top_problem(prediction) == top_problem(expected),
        "SP005": projected_loss_item(prediction) == projected_loss_item(expected),
        "SP006": severe_counts(prediction) == severe_counts(expected),
        "SP007": prediction.get("watch_list_summary", {}).get("monitoring_cadence")
        == expected["watch_list_summary"]["monitoring_cadence"],
    }
    total_weight = sum(weight for _, weight, _ in POINTS)
    earned = 0
    points = []
    for point_id, weight, description in POINTS:
        passed = bool(checks.get(point_id))
        earned += weight if passed else 0
        points.append({"id": point_id, "passed": passed, "weight": weight, "description": description})
    return {"score": round(earned / total_weight, 10), "max_score": 1.0, "points": points}


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "Usage: eval.py <prediction.json>"}))
        return 2
    expected_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        result = score_prediction(load_json(Path(sys.argv[1])), load_json(expected_path))
    except Exception as exc:
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "error": f"{type(exc).__name__}: {exc}",
            "points": [
                {"id": point_id, "passed": False, "weight": weight, "description": description}
                for point_id, weight, description in POINTS
            ],
        }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
