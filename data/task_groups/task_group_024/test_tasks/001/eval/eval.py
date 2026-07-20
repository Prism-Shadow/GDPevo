#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


CATEGORIES = ["NewFeature", "TechDebt", "Reliability", "Security"]

EXPECTED = {
    "scope_id": "test_001",
    "quarter": "2025-Q4",
    "teams": ["Data Platform", "Observability"],
    "product_area": "Data Reliability",
    "included_work_item_ids": [
        "WI-24024-005",
        "WI-24024-P041",
        "WI-24024-P042",
        "WI-24024-P043",
        "WI-24024-P044",
        "WI-24024-P045",
        "WI-24024-P046",
        "WI-24024-P047",
        "WI-24024-P048",
    ],
    "category_counts": {
        "NewFeature": 0,
        "TechDebt": 3,
        "Reliability": 4,
        "Security": 2,
    },
    "category_percentages_pct": {
        "NewFeature": 0.0,
        "TechDebt": 33.3,
        "Reliability": 44.4,
        "Security": 22.2,
    },
    "gap_table": [
        {"category": "NewFeature", "target_pct": 30.0, "actual_pct": 0.0, "gap_pct": -30.0},
        {"category": "TechDebt", "target_pct": 26.0, "actual_pct": 33.3, "gap_pct": 7.3},
        {"category": "Reliability", "target_pct": 28.0, "actual_pct": 44.4, "gap_pct": 16.4},
        {"category": "Security", "target_pct": 16.0, "actual_pct": 22.2, "gap_pct": 6.2},
    ],
    "under_invested_categories": ["NewFeature"],
    "category_owner_counts": {
        "NewFeature": {},
        "TechDebt": {"Devon Wells": 2, "Liam Chen": 1},
        "Reliability": {"Devon Wells": 1, "Liam Chen": 2, "UNASSIGNED": 1},
        "Security": {"Avery Quinn": 1, "Liam Chen": 1},
    },
    "category_team_counts": {
        "NewFeature": {},
        "TechDebt": {"Data Platform": 1, "Observability": 2},
        "Reliability": {"Data Platform": 3, "Observability": 1},
        "Security": {"Data Platform": 1, "Observability": 1},
    },
    "excluded_work_item_ids": [
        "WI-24024-P049",
        "WI-24024-P050",
        "WI-24024-P051",
    ],
    "excluded_reason_counts": {
        "cancelled": 1,
        "duplicate_status": 1,
        "duplicate_of": 2,
    },
    "recommended_action": "REBALANCE_CAPACITY",
}

RUBRIC = [
    ("included_work_item_ids", 2, "Correct qualifying Q4 portfolio work item set."),
    ("category_counts", 2, "Correct category counts after portfolio classification."),
    ("category_percentages_pct", 1, "Correct actual category percentages rounded to 1 decimal place."),
    ("gap_table", 1, "Correct target percentage and actual-minus-target gap table."),
    ("under_invested_categories", 1, "Correct under-invested category list ordered by deficit."),
    ("category_owner_counts", 2, "Correct owner counts by portfolio category."),
    ("category_team_counts", 2, "Correct team counts by portfolio category."),
    ("excluded_work_item_ids", 3, "Correct Q4 same-scope excluded candidate ids."),
    ("excluded_reason_counts", 2, "Correct exclusion reason counts for same-scope candidates."),
    ("recommended_action", 3, "Correct recommended action enum."),
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def norm_str(value):
    return str(value).strip() if value is not None else ""


def norm_set_list(value):
    if not isinstance(value, list):
        return None
    return sorted({norm_str(v) for v in value})


def one_decimal(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number + 0.0, 1)


def norm_counts(value):
    if not isinstance(value, dict):
        return None
    out = {}
    for category in CATEGORIES:
        raw = value.get(category)
        if isinstance(raw, bool):
            return None
        try:
            number = int(raw)
        except (TypeError, ValueError):
            return None
        if number != raw and not (isinstance(raw, str) and raw.strip() == str(number)):
            return None
        out[category] = number
    if set(value.keys()) != set(CATEGORIES):
        return None
    return out


def norm_nested_counts(value, outer_keys):
    if not isinstance(value, dict) or set(value.keys()) != set(outer_keys):
        return None
    out = {}
    for outer in outer_keys:
        inner = value.get(outer)
        if not isinstance(inner, dict):
            return None
        inner_out = {}
        for key, raw in inner.items():
            label = norm_str(key)
            if not label:
                return None
            if isinstance(raw, bool):
                return None
            try:
                number = int(raw)
            except (TypeError, ValueError):
                return None
            if number != raw and not (isinstance(raw, str) and raw.strip() == str(number)):
                return None
            if number:
                inner_out[label] = number
        out[outer] = dict(sorted(inner_out.items()))
    return out


def norm_reason_counts(value):
    keys = ["cancelled", "duplicate_status", "duplicate_of"]
    if not isinstance(value, dict) or set(value.keys()) != set(keys):
        return None
    out = {}
    for key in keys:
        raw = value.get(key)
        if isinstance(raw, bool):
            return None
        try:
            number = int(raw)
        except (TypeError, ValueError):
            return None
        if number != raw and not (isinstance(raw, str) and raw.strip() == str(number)):
            return None
        out[key] = number
    return out


def norm_percent_object(value):
    if not isinstance(value, dict) or set(value.keys()) != set(CATEGORIES):
        return None
    out = {}
    for category in CATEGORIES:
        rounded = one_decimal(value.get(category))
        if rounded is None:
            return None
        out[category] = rounded
    return out


def norm_gap_table(value):
    if not isinstance(value, list) or len(value) != len(CATEGORIES):
        return None
    out = []
    for row in value:
        if not isinstance(row, dict):
            return None
        category = norm_str(row.get("category"))
        if category not in CATEGORIES:
            return None
        normalized = {"category": category}
        for key in ("target_pct", "actual_pct", "gap_pct"):
            rounded = one_decimal(row.get(key))
            if rounded is None:
                return None
            normalized[key] = rounded
        out.append(normalized)
    return out


def ordered_str_list(value):
    if not isinstance(value, list):
        return None
    return [norm_str(v) for v in value]


def check_included(answer):
    actual = norm_set_list(answer.get("included_work_item_ids"))
    expected = norm_set_list(EXPECTED["included_work_item_ids"])
    return actual == expected, {"actual": actual, "expected": expected}


def check_counts(answer):
    actual = norm_counts(answer.get("category_counts"))
    expected = EXPECTED["category_counts"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_percentages(answer):
    actual = norm_percent_object(answer.get("category_percentages_pct"))
    expected = EXPECTED["category_percentages_pct"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_gap_table(answer):
    actual = norm_gap_table(answer.get("gap_table"))
    expected = EXPECTED["gap_table"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_under_invested(answer):
    actual = ordered_str_list(answer.get("under_invested_categories"))
    expected = EXPECTED["under_invested_categories"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_owner_counts(answer):
    actual = norm_nested_counts(answer.get("category_owner_counts"), CATEGORIES)
    expected = EXPECTED["category_owner_counts"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_team_counts(answer):
    actual = norm_nested_counts(answer.get("category_team_counts"), CATEGORIES)
    expected = EXPECTED["category_team_counts"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_excluded(answer):
    actual = norm_set_list(answer.get("excluded_work_item_ids"))
    expected = norm_set_list(EXPECTED["excluded_work_item_ids"])
    return actual == expected, {"actual": actual, "expected": expected}


def check_reason_counts(answer):
    actual = norm_reason_counts(answer.get("excluded_reason_counts"))
    expected = EXPECTED["excluded_reason_counts"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_action(answer):
    actual = norm_str(answer.get("recommended_action"))
    expected = EXPECTED["recommended_action"]
    return actual == expected, {"actual": actual, "expected": expected}


CHECKS = {
    "included_work_item_ids": check_included,
    "category_counts": check_counts,
    "category_percentages_pct": check_percentages,
    "gap_table": check_gap_table,
    "under_invested_categories": check_under_invested,
    "category_owner_counts": check_owner_counts,
    "category_team_counts": check_team_counts,
    "excluded_work_item_ids": check_excluded,
    "excluded_reason_counts": check_reason_counts,
    "recommended_action": check_action,
}


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "points": 0,
                    "max_score": sum(weight for _, weight, _ in RUBRIC),
                    "error": "Usage: eval.py /path/to/answer.json",
                }
            )
        )
        return 1

    answer_path = Path(sys.argv[1])
    max_points = sum(weight for _, weight, _ in RUBRIC)

    try:
        answer = load_json(answer_path)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "points": 0,
                    "max_score": max_points,
                    "error": f"Could not parse JSON: {exc}",
                    "details": [],
                },
                sort_keys=True,
            )
        )
        return 0

    details = []
    earned = 0
    for key, weight, description in RUBRIC:
        passed, check_details = CHECKS[key](answer)
        if passed:
            earned += weight
        details.append(
            {
                "id": key,
                "description": description,
                "weight": weight,
                "passed": passed,
                "earned": weight if passed else 0,
                "details": check_details,
            }
        )

    result = {
        "score": round(earned / max_points, 6),
        "points": earned,
        "max_score": max_points,
        "details": details,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
