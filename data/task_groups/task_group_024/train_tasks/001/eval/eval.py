#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


CATEGORIES = ["NewFeature", "TechDebt", "Reliability", "Security"]

EXPECTED = {
    "scope": {
        "scope_id": "train_001",
        "quarter": "2025-Q4",
        "teams": ["Identity Services", "Platform Core"],
        "product_areas": ["Atlas Backend", "Identity"],
        "target_scope_id": "train_001",
        "total_included": 10,
    },
    "included_work_item_ids": [
        "WI-24024-075",
        "WI-24024-098",
        "WI-24024-P001",
        "WI-24024-P002",
        "WI-24024-P003",
        "WI-24024-P004",
        "WI-24024-P005",
        "WI-24024-P006",
        "WI-24024-P007",
        "WI-24024-P008",
    ],
    "category_counts": {
        "NewFeature": 0,
        "TechDebt": 2,
        "Reliability": 3,
        "Security": 5,
    },
    "category_percentages": {
        "NewFeature": 0.0,
        "TechDebt": 20.0,
        "Reliability": 30.0,
        "Security": 50.0,
    },
    "gap_table": {
        "NewFeature": {"target_pct": 34.0, "actual_pct": 0.0, "gap_pct": -34.0},
        "TechDebt": {"target_pct": 24.0, "actual_pct": 20.0, "gap_pct": -4.0},
        "Reliability": {"target_pct": 22.0, "actual_pct": 30.0, "gap_pct": 8.0},
        "Security": {"target_pct": 20.0, "actual_pct": 50.0, "gap_pct": 30.0},
    },
    "under_invested_categories": ["NewFeature", "TechDebt"],
    "follow_up_action": {
        "action": "REBALANCE_CAPACITY",
        "primary_category": "NewFeature",
        "secondary_category": "TechDebt",
        "rationale_code": "LARGEST_NEGATIVE_GAP",
    },
    "exclusion_flags": {
        "excluded_duplicate_ids": ["WI-24024-P009", "WI-24024-P011"],
        "excluded_cancelled_ids": ["WI-24024-P010"],
        "ignored_mirror_status_and_legacy_category": True,
    },
}

POINTS = [
    ("included_set", 3, "Correct included closed portfolio work item set."),
    ("category_counts", 3, "Correct count of included items by portfolio category."),
    ("percentages", 2, "Correct one-decimal actual percentage mix by category."),
    ("gap_table", 2, "Correct target, actual, and gap percentage points by category."),
    ("under_invested_categories", 2, "Correct categories with negative target gaps."),
    ("follow_up_action", 1, "Correct controlled follow-up action and category focus."),
    ("exclusion_flags", 1, "Correct duplicate/cancelled exclusion flags and stale-field flag."),
]


def load_answer(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def unique_sorted_strings(value):
    if not isinstance(value, list):
        return None
    cleaned = []
    for item in value:
        if not isinstance(item, str):
            return None
        cleaned.append(item.strip())
    return sorted(set(cleaned))


def ordered_clean_strings(value):
    if not isinstance(value, list):
        return None
    cleaned = []
    for item in value:
        if not isinstance(item, str):
            return None
        cleaned.append(item.strip())
    return cleaned


def number_1dp(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if not math.isfinite(float(value)):
        return None
    return round(float(value), 1)


def normalize_counts(value):
    if not isinstance(value, dict):
        return None
    out = {}
    for category in CATEGORIES:
        item = value.get(category)
        if isinstance(item, bool) or not isinstance(item, int):
            return None
        out[category] = item
    return out


def normalize_percent_object(value):
    if not isinstance(value, dict):
        return None
    out = {}
    for category in CATEGORIES:
        rounded = number_1dp(value.get(category))
        if rounded is None:
            return None
        out[category] = rounded
    return out


def normalize_gap_table(value):
    if not isinstance(value, list):
        return None
    out = {}
    for row in value:
        if not isinstance(row, dict):
            return None
        category = row.get("category")
        if category not in CATEGORIES or category in out:
            return None
        target = number_1dp(row.get("target_pct"))
        actual = number_1dp(row.get("actual_pct"))
        gap = number_1dp(row.get("gap_pct"))
        if target is None or actual is None or gap is None:
            return None
        out[category] = {"target_pct": target, "actual_pct": actual, "gap_pct": gap}
    return out


def normalize_follow_up(value):
    if not isinstance(value, dict):
        return None
    return {
        "action": value.get("action"),
        "primary_category": value.get("primary_category"),
        "secondary_category": value.get("secondary_category"),
        "rationale_code": value.get("rationale_code"),
    }


def normalize_exclusion_flags(value):
    if not isinstance(value, dict):
        return None
    return {
        "excluded_duplicate_ids": unique_sorted_strings(value.get("excluded_duplicate_ids")),
        "excluded_cancelled_ids": unique_sorted_strings(value.get("excluded_cancelled_ids")),
        "ignored_mirror_status_and_legacy_category": value.get("ignored_mirror_status_and_legacy_category"),
    }


def check_scope(answer):
    scope = answer.get("scope") if isinstance(answer, dict) else None
    if not isinstance(scope, dict):
        return False, {"reason": "missing or invalid scope"}
    observed = {
        "scope_id": scope.get("scope_id"),
        "quarter": scope.get("quarter"),
        "teams": unique_sorted_strings(scope.get("teams")),
        "product_areas": unique_sorted_strings(scope.get("product_areas")),
        "target_scope_id": scope.get("target_scope_id"),
        "total_included": scope.get("total_included"),
    }
    expected = dict(EXPECTED["scope"])
    expected["teams"] = sorted(expected["teams"])
    expected["product_areas"] = sorted(expected["product_areas"])
    return observed == expected, {"expected": expected, "observed": observed}


def check_included_set(answer):
    observed = unique_sorted_strings(answer.get("included_work_item_ids"))
    expected = EXPECTED["included_work_item_ids"]
    scope_ok, scope_detail = check_scope(answer)
    passed = observed == expected and scope_ok
    return passed, {"expected_ids": expected, "observed_ids": observed, "scope": scope_detail}


def check_category_counts(answer):
    observed = normalize_counts(answer.get("category_counts"))
    return observed == EXPECTED["category_counts"], {
        "expected": EXPECTED["category_counts"],
        "observed": observed,
    }


def check_percentages(answer):
    observed = normalize_percent_object(answer.get("category_percentages"))
    return observed == EXPECTED["category_percentages"], {
        "expected": EXPECTED["category_percentages"],
        "observed": observed,
    }


def check_gap_table(answer):
    observed = normalize_gap_table(answer.get("gap_table"))
    return observed == EXPECTED["gap_table"], {
        "expected": EXPECTED["gap_table"],
        "observed": observed,
    }


def check_under_invested(answer):
    observed = ordered_clean_strings(answer.get("under_invested_categories"))
    expected = EXPECTED["under_invested_categories"]
    return observed == expected, {"expected": expected, "observed": observed}


def check_follow_up(answer):
    observed = normalize_follow_up(answer.get("follow_up_action"))
    expected = EXPECTED["follow_up_action"]
    return observed == expected, {"expected": expected, "observed": observed}


def check_exclusion_flags(answer):
    observed = normalize_exclusion_flags(answer.get("exclusion_flags"))
    expected = EXPECTED["exclusion_flags"]
    return observed == expected, {"expected": expected, "observed": observed}


CHECKS = {
    "included_set": check_included_set,
    "category_counts": check_category_counts,
    "percentages": check_percentages,
    "gap_table": check_gap_table,
    "under_invested_categories": check_under_invested,
    "follow_up_action": check_follow_up,
    "exclusion_flags": check_exclusion_flags,
}


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {"score": 0.0, "points": [], "max_score": 1.0, "error": "usage: eval.py ANSWER_JSON"},
                indent=2,
                sort_keys=True,
            )
        )
        sys.exit(2)

    try:
        answer = load_answer(Path(sys.argv[1]))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "points": [
                        {
                            "id": point_id,
                            "weight": weight,
                            "max_score": weight / sum(w for _, w, _ in POINTS),
                            "passed": False,
                            "earned_score": 0.0,
                            "details": {"error": f"failed to parse answer JSON: {exc}"},
                        }
                        for point_id, weight, _ in POINTS
                    ],
                    "max_score": 1.0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    total_weight = sum(weight for _, weight, _ in POINTS)
    point_results = []
    score = 0.0
    for point_id, weight, description in POINTS:
        max_score = weight / total_weight
        passed, details = CHECKS[point_id](answer)
        earned = max_score if passed else 0.0
        score += earned
        point_results.append(
            {
                "id": point_id,
                "description": description,
                "weight": weight,
                "max_score": round(max_score, 6),
                "passed": bool(passed),
                "earned_score": round(earned, 6),
                "details": details,
            }
        )

    print(
        json.dumps(
            {
                "score": round(score, 6),
                "points": point_results,
                "max_score": 1.0,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
