#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    ("SP001", 2, "target regrade count and exposure"),
    ("SP002", 3, "final rating exposure totals"),
    ("SP003", 3, "material downgrade loan IDs"),
    ("SP004", 2, "NPA ratio and FDIC variance"),
    ("SP005", 2, "top problem credit and action"),
    ("SP006", 2, "current-rating-3 migration distribution"),
    ("SP007", 1, "watch-list action coverage"),
]


def load_json(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def money(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def ratio(value):
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def bps(value):
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


def final_rating_totals(answer):
    rows = answer.get("portfolio_regrade", {}).get("final_rating_exposure_totals")
    if not isinstance(rows, list):
        return None
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        normalized.append(
            {
                "final_rating": as_int(row.get("final_rating")),
                "loan_count": as_int(row.get("loan_count")),
                "exposure": money(row.get("exposure")),
            }
        )
    return sorted(normalized, key=lambda row: row["final_rating"])


def material_ids(answer):
    rows = answer.get("material_downgrades")
    if not isinstance(rows, list):
        return None
    ids = []
    for row in rows:
        if isinstance(row, dict):
            ids.append(str(row.get("loan_id")))
        else:
            ids.append(str(row))
    return sorted(ids)


def migration_current_3(answer):
    rows = answer.get("portfolio_regrade", {}).get("migration_from_current_rating_3")
    if not isinstance(rows, list):
        return None
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        normalized.append(
            {
                "final_rating": as_int(row.get("final_rating")),
                "loan_count": as_int(row.get("loan_count")),
                "exposure": money(row.get("exposure")),
                "loan_ids": sorted_strings(row.get("loan_ids")),
            }
        )
    return sorted(normalized, key=lambda row: row["final_rating"])


def watch_list_coverage(answer):
    coverage = answer.get("portfolio_regrade", {}).get("watch_list_action_coverage")
    if not isinstance(coverage, dict):
        return None
    rows = coverage.get("by_action")
    if not isinstance(rows, list):
        return None
    normalized_rows = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        normalized_rows.append(
            {
                "action": str(row.get("action")),
                "loan_count": as_int(row.get("loan_count")),
                "exposure": money(row.get("exposure")),
                "loan_ids": sorted_strings(row.get("loan_ids")),
            }
        )
    return {
        "covered_loan_count": as_int(coverage.get("covered_loan_count")),
        "covered_exposure": money(coverage.get("covered_exposure")),
        "by_action": sorted(normalized_rows, key=lambda row: row["action"]),
    }


def score_prediction(prediction, expected):
    checks = {
        "SP001": (
            prediction.get("branch_id") == expected.get("branch_id")
            and prediction.get("review_date") == expected.get("review_date")
            and as_int(prediction.get("portfolio_regrade", {}).get("target_current_rating_min"))
            == expected["portfolio_regrade"]["target_current_rating_min"]
            and as_int(prediction.get("portfolio_regrade", {}).get("target_loan_count"))
            == expected["portfolio_regrade"]["target_loan_count"]
            and money(prediction.get("portfolio_regrade", {}).get("target_exposure"))
            == money(expected["portfolio_regrade"]["target_exposure"])
        ),
        "SP002": final_rating_totals(prediction) == final_rating_totals(expected),
        "SP003": material_ids(prediction) == material_ids(expected),
        "SP004": (
            prediction.get("npa_benchmark", {}).get("benchmark_version")
            == expected["npa_benchmark"]["benchmark_version"]
            and prediction.get("npa_benchmark", {}).get("benchmark_metric")
            == expected["npa_benchmark"]["benchmark_metric"]
            and money(prediction.get("npa_benchmark", {}).get("branch_npa_exposure"))
            == money(expected["npa_benchmark"]["branch_npa_exposure"])
            and money(prediction.get("npa_benchmark", {}).get("branch_total_loans"))
            == money(expected["npa_benchmark"]["branch_total_loans"])
            and ratio(prediction.get("npa_benchmark", {}).get("branch_npa_ratio"))
            == ratio(expected["npa_benchmark"]["branch_npa_ratio"])
            and ratio(prediction.get("npa_benchmark", {}).get("fdic_benchmark_ratio"))
            == ratio(expected["npa_benchmark"]["fdic_benchmark_ratio"])
            and ratio(prediction.get("npa_benchmark", {}).get("variance_ratio"))
            == ratio(expected["npa_benchmark"]["variance_ratio"])
            and bps(prediction.get("npa_benchmark", {}).get("variance_bps"))
            == bps(expected["npa_benchmark"]["variance_bps"])
        ),
        "SP005": (
            prediction.get("top_problem_credit", {}).get("loan_id") == expected["top_problem_credit"]["loan_id"]
            and money(prediction.get("top_problem_credit", {}).get("exposure"))
            == money(expected["top_problem_credit"]["exposure"])
            and as_int(prediction.get("top_problem_credit", {}).get("final_rating"))
            == expected["top_problem_credit"]["final_rating"]
            and prediction.get("top_problem_credit", {}).get("payment_status")
            == expected["top_problem_credit"]["payment_status"]
            and prediction.get("top_problem_credit", {}).get("recommended_action")
            == expected["top_problem_credit"]["recommended_action"]
        ),
        "SP006": migration_current_3(prediction) == migration_current_3(expected),
        "SP007": watch_list_coverage(prediction) == watch_list_coverage(expected),
    }
    results = []
    total_weight = sum(weight for _, weight, _ in POINTS)
    earned = 0
    for point_id, weight, description in POINTS:
        passed = bool(checks.get(point_id))
        if passed:
            earned += weight
        results.append(
            {
                "id": point_id,
                "passed": passed,
                "weight": weight,
                "description": description,
            }
        )
    return {
        "score": round(earned / total_weight, 10),
        "max_score": 1.0,
        "points": results,
    }


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "Usage: eval.py <prediction.json>"}))
        return 2
    prediction_path = Path(sys.argv[1])
    expected_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        prediction = load_json(prediction_path)
        expected = load_json(expected_path)
        result = score_prediction(prediction, expected)
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
