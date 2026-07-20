#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


CATEGORIES = ["NewFeature", "TechDebt", "Reliability", "Security"]
EXPECTED_P_SERIES_IDS = [
    "WI-24024-P061",
    "WI-24024-P062",
    "WI-24024-P063",
    "WI-24024-P064",
    "WI-24024-P065",
    "WI-24024-P066",
    "WI-24024-P067",
    "WI-24024-P068",
]
EXPECTED_LEGACY_IDS = [
    "WI-24024-123",
    "WI-24024-150",
]
EXCLUDED_DISTRACTOR_IDS = [
    "WI-24024-053",
    "WI-24024-122",
    "WI-24024-P069",
    "WI-24024-P070",
    "WI-24024-P071",
]

EXPECTED = {
    "included_work_item_ids": [
        "WI-24024-123",
        "WI-24024-150",
        "WI-24024-P061",
        "WI-24024-P062",
        "WI-24024-P063",
        "WI-24024-P064",
        "WI-24024-P065",
        "WI-24024-P066",
        "WI-24024-P067",
        "WI-24024-P068",
    ],
    "category_counts": {
        "NewFeature": 2,
        "TechDebt": 1,
        "Reliability": 3,
        "Security": 4,
    },
    "gap_table": [
        {"category": "NewFeature", "target_pct": 36.0, "actual_pct": 20.0, "gap_pct": -16.0},
        {"category": "TechDebt", "target_pct": 22.0, "actual_pct": 10.0, "gap_pct": -12.0},
        {"category": "Reliability", "target_pct": 20.0, "actual_pct": 30.0, "gap_pct": 10.0},
        {"category": "Security", "target_pct": 22.0, "actual_pct": 40.0, "gap_pct": 18.0},
    ],
    "under_invested_categories": ["NewFeature", "TechDebt"],
    "action_owner_teams": [
        {"category": "NewFeature", "owner_teams": ["API Foundations", "Revenue Platform"]},
        {"category": "TechDebt", "owner_teams": ["Integrations"]},
    ],
    "evidence_ids_by_category": {
        "NewFeature": ["WI-24024-P061", "WI-24024-P064"],
        "TechDebt": ["WI-24024-P067"],
        "Reliability": [
            "WI-24024-123",
            "WI-24024-P063",
            "WI-24024-P066",
        ],
        "Security": [
            "WI-24024-150",
            "WI-24024-P062",
            "WI-24024-P065",
            "WI-24024-P068",
        ],
    },
}

RUBRIC = [
    (
        "SP001",
        "p_series_included_set",
        3,
        "Correct included P-series Q4 work item set for the scoped teams and product areas.",
    ),
    (
        "SP002",
        "legacy_included_set",
        1,
        "Correct included legacy Q4 work item set for the scoped teams and product areas.",
    ),
    (
        "SP003",
        "excluded_distractors_absent",
        3,
        "Cancelled, duplicate-status, and duplicate-of distractors are absent from the included set.",
    ),
    ("SP004", "category_counts", 1, "Correct final portfolio category counts."),
    ("SP005", "sorted_gap_table", 1, "Correct sorted target, actual, and gap table."),
    ("SP006", "under_invested_categories", 1, "Correct under-invested categories ordered by deficit."),
    ("SP007", "action_owner_teams", 1, "Correct owner teams for follow-up on under-invested categories."),
    ("SP008", "evidence_ids_by_category", 1, "Correct included evidence ids grouped by final category."),
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


def norm_string(value):
    if value is None:
        return ""
    return str(value).strip()


def sorted_unique_strings(value):
    if not isinstance(value, list):
        return None
    return sorted({norm_string(item) for item in value if norm_string(item)})


def ordered_strings(value):
    if not isinstance(value, list):
        return None
    return [norm_string(item) for item in value]


def norm_int(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if isinstance(value, str):
        return number if value.strip() == str(number) else None
    if number != value:
        return None
    return number


def norm_pct(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number + 0.0, 1)


def normalize_counts(value):
    if not isinstance(value, dict) or set(value.keys()) != set(CATEGORIES):
        return None
    out = {}
    for category in CATEGORIES:
        number = norm_int(value.get(category))
        if number is None:
            return None
        out[category] = number
    return out


def normalize_gap_table(value):
    if not isinstance(value, list) or len(value) != len(CATEGORIES):
        return None
    rows = []
    for row in value:
        if not isinstance(row, dict):
            return None
        category = norm_string(row.get("category"))
        if category not in CATEGORIES:
            return None
        normalized = {"category": category}
        for key in ("target_pct", "actual_pct", "gap_pct"):
            pct = norm_pct(row.get(key))
            if pct is None:
                return None
            normalized[key] = pct
        rows.append(normalized)
    return rows


def normalize_action_owner_teams(value):
    if not isinstance(value, list):
        return None
    rows = []
    for row in value:
        if not isinstance(row, dict):
            return None
        category = norm_string(row.get("category"))
        if category not in CATEGORIES:
            return None
        owner_teams = sorted_unique_strings(row.get("owner_teams"))
        if owner_teams is None:
            return None
        rows.append({"category": category, "owner_teams": owner_teams})
    return rows


def normalize_evidence(value):
    if not isinstance(value, dict) or set(value.keys()) != set(CATEGORIES):
        return None
    out = {}
    for category in CATEGORIES:
        ids = sorted_unique_strings(value.get(category))
        if ids is None:
            return None
        out[category] = ids
    return out


def make_point(point_id, key, weight, goal, passed, details):
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
    actual_p_series = (
        None
        if actual_included is None
        else sorted([item for item in actual_included if item.startswith("WI-24024-P")])
    )
    actual_legacy = (
        None
        if actual_included is None
        else sorted(
            [
                item
                for item in actual_included
                if item not in EXPECTED_P_SERIES_IDS and item not in EXCLUDED_DISTRACTOR_IDS
            ]
        )
    )
    excluded_present = None if actual_included is None else sorted(set(actual_included) & set(EXCLUDED_DISTRACTOR_IDS))
    points.append(
        make_point(
            *RUBRIC[0],
            passed=actual_p_series == EXPECTED_P_SERIES_IDS,
            details={"expected": EXPECTED_P_SERIES_IDS, "actual": actual_p_series},
        )
    )

    points.append(
        make_point(
            *RUBRIC[1],
            passed=actual_legacy == EXPECTED_LEGACY_IDS,
            details={"expected": EXPECTED_LEGACY_IDS, "actual": actual_legacy},
        )
    )

    points.append(
        make_point(
            *RUBRIC[2],
            passed=excluded_present == [],
            details={
                "excluded_ids_that_should_be_absent": EXCLUDED_DISTRACTOR_IDS,
                "actual_present": excluded_present,
            },
        )
    )

    actual_counts = normalize_counts(candidate.get("category_counts"))
    points.append(
        make_point(
            *RUBRIC[3],
            passed=actual_counts == EXPECTED["category_counts"],
            details={"expected": EXPECTED["category_counts"], "actual": actual_counts},
        )
    )

    actual_gap_table = normalize_gap_table(candidate.get("gap_table"))
    points.append(
        make_point(
            *RUBRIC[4],
            passed=actual_gap_table == EXPECTED["gap_table"],
            details={"expected": EXPECTED["gap_table"], "actual": actual_gap_table},
        )
    )

    actual_under_invested = ordered_strings(candidate.get("under_invested_categories"))
    points.append(
        make_point(
            *RUBRIC[5],
            passed=actual_under_invested == EXPECTED["under_invested_categories"],
            details={"expected": EXPECTED["under_invested_categories"], "actual": actual_under_invested},
        )
    )

    actual_owners = normalize_action_owner_teams(candidate.get("action_owner_teams"))
    points.append(
        make_point(
            *RUBRIC[6],
            passed=actual_owners == EXPECTED["action_owner_teams"],
            details={"expected": EXPECTED["action_owner_teams"], "actual": actual_owners},
        )
    )

    actual_evidence = normalize_evidence(candidate.get("evidence_ids_by_category"))
    points.append(
        make_point(
            *RUBRIC[7],
            passed=actual_evidence == EXPECTED["evidence_ids_by_category"],
            details={"expected": EXPECTED["evidence_ids_by_category"], "actual": actual_evidence},
        )
    )

    earned = sum(item["earned"] for item in points)
    max_score = sum(item["weight"] for item in points)
    result = {
        "score": round(earned / max_score, 6) if max_score else 0.0,
        "points": earned,
        "max_score": max_score,
        "details": points,
    }
    if parse_error:
        result["parse_error"] = parse_error
    return result


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "points": 0,
                    "max_score": sum(item[2] for item in RUBRIC),
                    "error": "Usage: eval.py /path/to/answer.json",
                    "details": [],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    candidate, parse_error = load_candidate(sys.argv[1])
    print(json.dumps(evaluate(candidate, parse_error), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
