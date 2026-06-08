#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    ("SP001", 2, "weighted CDFI scores for both CRE applications"),
    ("SP002", 2, "stressed DSCR values and breach flags"),
    ("SP003", 3, "selected application and path enum"),
    ("SP004", 2, "post-approval CRE concentration"),
    ("SP005", 2, "FDIC delinquency benchmark variance"),
    ("SP006", 2, "condition set for selected credit"),
    ("SP007", 1, "deferral reason set for unselected credit"),
]


def load_json(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def num(value, digits):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def sorted_list(values):
    if not isinstance(values, list):
        return None
    return sorted(str(v) for v in values)


def app_rows(answer):
    rows = answer.get("applications_compared")
    if not isinstance(rows, list):
        return None
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        normalized.append(
            {
                "application_id": str(row.get("application_id")),
                "weighted_cdfi_score": num(row.get("weighted_cdfi_score"), 1),
                "score_class": str(row.get("score_class")),
                "decision": str(row.get("decision")),
                "reason_codes": sorted_list(row.get("reason_codes")),
            }
        )
    return sorted(normalized, key=lambda row: row["application_id"])


def stress_rows(answer):
    rows = answer.get("stress", {}).get("results")
    if not isinstance(rows, list):
        return None
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        normalized.append(
            {
                "application_id": str(row.get("application_id")),
                "base_dscr": num(row.get("base_dscr"), 2),
                "stressed_dscr": num(row.get("stressed_dscr"), 2),
                "breaches_threshold": bool(row.get("breaches_threshold")),
            }
        )
    return sorted(normalized, key=lambda row: row["application_id"])


def score_prediction(prediction, expected):
    checks = {
        "SP001": [
            (r["application_id"], r["weighted_cdfi_score"], r["score_class"]) for r in (app_rows(prediction) or [])
        ]
        == [(r["application_id"], r["weighted_cdfi_score"], r["score_class"]) for r in (app_rows(expected) or [])],
        "SP002": stress_rows(prediction) == stress_rows(expected)
        and num(prediction.get("stress", {}).get("coverage_breach_threshold"), 2)
        == num(expected["stress"]["coverage_breach_threshold"], 2),
        "SP003": prediction.get("branch_id") == expected.get("branch_id")
        and prediction.get("recommended_path", {}).get("selected_application_id")
        == expected["recommended_path"]["selected_application_id"]
        and prediction.get("recommended_path", {}).get("path") == expected["recommended_path"]["path"]
        and prediction.get("recommended_path", {}).get("unselected_application_id")
        == expected["recommended_path"]["unselected_application_id"]
        and prediction.get("recommended_path", {}).get("unselected_disposition")
        == expected["recommended_path"]["unselected_disposition"],
        "SP004": num(prediction.get("concentration", {}).get("cre_policy_limit_pct"), 4)
        == num(expected["concentration"]["cre_policy_limit_pct"], 4)
        and num(prediction.get("concentration", {}).get("existing_cre_exposure"), 2)
        == num(expected["concentration"]["existing_cre_exposure"], 2)
        and num(prediction.get("concentration", {}).get("existing_cre_concentration"), 4)
        == num(expected["concentration"]["existing_cre_concentration"], 4)
        and num(prediction.get("concentration", {}).get("selected_post_approval_cre_concentration"), 4)
        == num(expected["concentration"]["selected_post_approval_cre_concentration"], 4)
        and num(prediction.get("concentration", {}).get("selected_policy_variance_bps"), 2)
        == num(expected["concentration"]["selected_policy_variance_bps"], 2),
        "SP005": prediction.get("concentration", {}).get("fdic_benchmark_metric")
        == expected["concentration"]["fdic_benchmark_metric"]
        and num(prediction.get("concentration", {}).get("branch_delinquency_ratio"), 4)
        == num(expected["concentration"]["branch_delinquency_ratio"], 4)
        and num(prediction.get("concentration", {}).get("fdic_benchmark_ratio"), 4)
        == num(expected["concentration"]["fdic_benchmark_ratio"], 4)
        and num(prediction.get("concentration", {}).get("fdic_variance_ratio"), 4)
        == num(expected["concentration"]["fdic_variance_ratio"], 4)
        and num(prediction.get("concentration", {}).get("fdic_variance_bps"), 2)
        == num(expected["concentration"]["fdic_variance_bps"], 2),
        "SP006": sorted_list(prediction.get("conditions")) == sorted_list(expected.get("conditions")),
        "SP007": sorted_list(prediction.get("recommended_path", {}).get("unselected_reason_codes"))
        == sorted_list(expected["recommended_path"]["unselected_reason_codes"]),
    }
    total_weight = sum(weight for _, weight, _ in POINTS)
    earned = 0
    results = []
    for point_id, weight, description in POINTS:
        passed = bool(checks.get(point_id))
        if passed:
            earned += weight
        results.append({"id": point_id, "passed": passed, "weight": weight, "description": description})
    return {"score": round(earned / total_weight, 10), "max_score": 1.0, "points": results}


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
