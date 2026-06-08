#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    ("SP001", 3, "CRE recommendation and participation requirement for SOU-APP-901"),
    ("SP002", 2, "stressed DSCR and post-participation concentration"),
    ("SP003", 2, "approved application set"),
    ("SP004", 2, "conditional approval application set"),
    ("SP005", 2, "declined application set"),
    ("SP006", 2, "framework selection for consumer, residential, C&I, and SBA applications"),
    ("SP007", 2, "committed and remaining capacity"),
    ("SP008", 1, "low-FICO consumer decline reason"),
    ("SP009", 2, "C&I approval conditions"),
]


def load_json(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def num(value, digits):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def sorted_list(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item) for item in value)


def path_get(obj, *keys):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def score_prediction(prediction, expected):
    checks = {
        "SP001": prediction.get("branch_id") == expected.get("branch_id")
        and path_get(prediction, "recommended_path", "selected_application_id") == "SOU-APP-901"
        and path_get(prediction, "recommended_path", "path") == "participation_required"
        and sorted_list(path_get(prediction, "recommended_path", "reason_codes"))
        == sorted_list(path_get(expected, "recommended_path", "reason_codes"))
        and "participation_required" in (path_get(prediction, "conditions", "by_application", "SOU-APP-901") or []),
        "SP002": num(path_get(prediction, "stress", "base_dscr"), 2)
        == num(path_get(expected, "stress", "base_dscr"), 2)
        and num(path_get(prediction, "stress", "stressed_dscr"), 2)
        == num(path_get(expected, "stress", "stressed_dscr"), 2)
        and bool(path_get(prediction, "stress", "breaches_threshold"))
        == bool(path_get(expected, "stress", "breaches_threshold"))
        and num(path_get(prediction, "concentration", "retained_cre_amount"), 2)
        == num(path_get(expected, "concentration", "retained_cre_amount"), 2)
        and num(path_get(prediction, "concentration", "post_participation_cre_concentration"), 4)
        == num(path_get(expected, "concentration", "post_participation_cre_concentration"), 4),
        "SP003": sorted_list(path_get(prediction, "decisions", "approved"))
        == sorted_list(path_get(expected, "decisions", "approved")),
        "SP004": sorted_list(path_get(prediction, "decisions", "conditional_approved"))
        == sorted_list(path_get(expected, "decisions", "conditional_approved")),
        "SP005": sorted_list(path_get(prediction, "decisions", "declined"))
        == sorted_list(path_get(expected, "decisions", "declined")),
        "SP006": path_get(prediction, "framework_assignments", "SOU-APP-004")
        == path_get(expected, "framework_assignments", "SOU-APP-004")
        and path_get(prediction, "framework_assignments", "SOU-APP-005")
        == path_get(expected, "framework_assignments", "SOU-APP-005")
        and path_get(prediction, "framework_assignments", "SOU-APP-002")
        == path_get(expected, "framework_assignments", "SOU-APP-002")
        and path_get(prediction, "framework_assignments", "SOU-APP-902")
        == path_get(expected, "framework_assignments", "SOU-APP-902")
        and path_get(prediction, "framework_assignments", "SOU-APP-003")
        == path_get(expected, "framework_assignments", "SOU-APP-003"),
        "SP007": num(path_get(prediction, "allocation", "committed_capacity_amount"), 2)
        == num(path_get(expected, "allocation", "committed_capacity_amount"), 2)
        and num(path_get(prediction, "allocation", "remaining_capacity"), 2)
        == num(path_get(expected, "allocation", "remaining_capacity"), 2),
        "SP008": sorted_list(path_get(prediction, "conditions", "decline_reasons", "SOU-APP-005"))
        == sorted_list(path_get(expected, "conditions", "decline_reasons", "SOU-APP-005")),
        "SP009": sorted_list(path_get(prediction, "conditions", "by_application", "SOU-APP-902"))
        == sorted_list(path_get(expected, "conditions", "by_application", "SOU-APP-902")),
    }
    total = sum(weight for _, weight, _ in POINTS)
    earned = 0
    results = []
    for point_id, weight, description in POINTS:
        passed = bool(checks.get(point_id))
        earned += weight if passed else 0
        results.append({"id": point_id, "passed": passed, "weight": weight, "description": description})
    return {"score": round(earned / total, 10), "max_score": 1.0, "points": results}


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
            "points": [{"id": p, "passed": False, "weight": w, "description": d} for p, w, d in POINTS],
        }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
