#!/usr/bin/env python3
import json
import sys
from pathlib import Path


CATEGORIES = ["NewFeature", "TechDebt", "Reliability", "Security"]

EXPECTED = {
    "included_work_item_ids": [
        "WI-24024-P021",
        "WI-24024-007",
        "WI-24024-P022",
        "WI-24024-P023",
        "WI-24024-P024",
        "WI-24024-P025",
        "WI-24024-P026",
        "WI-24024-P027",
        "WI-24024-P028",
    ],
    "category_counts": {
        "NewFeature": 1,
        "TechDebt": 1,
        "Reliability": 4,
        "Security": 3,
    },
    "mix_table": {
        "NewFeature": {"count": 1, "actual_pct": 11.1, "target_pct": 42.0, "gap_pct": -30.9},
        "TechDebt": {"count": 1, "actual_pct": 11.1, "target_pct": 20.0, "gap_pct": -8.9},
        "Reliability": {"count": 4, "actual_pct": 44.4, "target_pct": 24.0, "gap_pct": 20.4},
        "Security": {"count": 3, "actual_pct": 33.3, "target_pct": 14.0, "gap_pct": 19.3},
    },
    "largest_deficit_category": "NewFeature",
    "action_owner_team": "Growth Experiences",
    "excluded_distractor_ids": [
        "WI-24024-P029",
        "WI-24024-P030",
        "WI-24024-P031",
    ],
}

RUBRIC = [
    ("SP001", "included_set", 3, "Correct included closed work item set"),
    ("SP002", "category_counts", 3, "Correct portfolio category counts"),
    ("SP003", "gap_table", 2, "Correct count, actual, target, and gap table"),
    ("SP004", "largest_deficit_category", 2, "Correct largest deficit category"),
    ("SP005", "action_owner_team", 1, "Correct recommended action owner team"),
    ("SP006", "excluded_distractors", 1, "Correct excluded same-scope Q4 distractor set"),
]


def load_candidate(path):
    try:
        with Path(path).open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}, "top-level JSON value must be an object"
        return data, None
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def sorted_unique_strings(value):
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()})


def norm_string(value):
    if value is None:
        return ""
    return str(value).strip()


def norm_int(value):
    try:
        if isinstance(value, bool):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def norm_pct(value):
    try:
        if isinstance(value, bool):
            return None
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def normalize_counts(value):
    if not isinstance(value, dict):
        return {}
    return {category: norm_int(value.get(category)) for category in CATEGORIES}


def normalize_mix_table(value):
    if not isinstance(value, list):
        return {}
    rows = {}
    for row in value:
        if not isinstance(row, dict):
            continue
        category = norm_string(row.get("category"))
        if category not in CATEGORIES:
            continue
        rows[category] = {
            "count": norm_int(row.get("count")),
            "actual_pct": norm_pct(row.get("actual_pct")),
            "target_pct": norm_pct(row.get("target_pct")),
            "gap_pct": norm_pct(row.get("gap_pct")),
        }
    return rows


def point(point_id, key, weight, goal, passed, details):
    return {
        "id": point_id,
        "key": key,
        "goal": goal,
        "weight": weight,
        "passed": bool(passed),
        "earned": weight if passed else 0,
        "details": details,
    }


def evaluate(candidate, parse_error=None):
    points = []

    actual_included = sorted_unique_strings(candidate.get("included_work_item_ids"))
    expected_included = sorted_unique_strings(EXPECTED["included_work_item_ids"])
    points.append(
        point(
            *RUBRIC[0],
            passed=actual_included == expected_included,
            details={"expected": expected_included, "actual": actual_included},
        )
    )

    actual_counts = normalize_counts(candidate.get("category_counts"))
    points.append(
        point(
            *RUBRIC[1],
            passed=actual_counts == EXPECTED["category_counts"],
            details={"expected": EXPECTED["category_counts"], "actual": actual_counts},
        )
    )

    actual_mix = normalize_mix_table(candidate.get("mix_table"))
    points.append(
        point(
            *RUBRIC[2],
            passed=actual_mix == EXPECTED["mix_table"],
            details={"expected": EXPECTED["mix_table"], "actual": actual_mix},
        )
    )

    actual_deficit = norm_string(candidate.get("largest_deficit_category"))
    points.append(
        point(
            *RUBRIC[3],
            passed=actual_deficit == EXPECTED["largest_deficit_category"],
            details={"expected": EXPECTED["largest_deficit_category"], "actual": actual_deficit},
        )
    )

    action = candidate.get("recommended_action")
    actual_owner = norm_string(action.get("owner_team")) if isinstance(action, dict) else ""
    points.append(
        point(
            *RUBRIC[4],
            passed=actual_owner == EXPECTED["action_owner_team"],
            details={"expected": EXPECTED["action_owner_team"], "actual": actual_owner},
        )
    )

    actual_excluded = sorted_unique_strings(candidate.get("excluded_distractor_ids"))
    expected_excluded = sorted_unique_strings(EXPECTED["excluded_distractor_ids"])
    points.append(
        point(
            *RUBRIC[5],
            passed=actual_excluded == expected_excluded,
            details={"expected": expected_excluded, "actual": actual_excluded},
        )
    )

    earned_raw = sum(item["earned"] for item in points)
    max_raw = sum(item["weight"] for item in points)
    normalized_score = round(earned_raw / max_raw, 6) if max_raw else 0.0
    result = {
        "score": normalized_score,
        "max_score": 1.0,
        "earned_raw": earned_raw,
        "max_raw": max_raw,
        "points": points,
    }
    if parse_error:
        result["parse_error"] = parse_error
    return result


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {"score": 0, "max_score": 12, "points": [], "error": "usage: eval.py <candidate_answer_json>"},
                indent=2,
            )
        )
        return 2

    candidate, parse_error = load_candidate(sys.argv[1])
    print(json.dumps(evaluate(candidate, parse_error), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
