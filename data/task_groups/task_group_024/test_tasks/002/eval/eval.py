#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED = {
    "included_primary_ids": [
        "WI-24024-036",
        "WI-24024-046",
        "WI-24024-074",
        "WI-24024-096",
        "WI-24024-110",
        "WI-24024-119",
        "WI-24024-S041",
        "WI-24024-S042",
        "WI-24024-S043",
        "WI-24024-S044",
        "WI-24024-S045",
        "WI-24024-S046",
        "WI-24024-S047",
        "WI-24024-S048",
    ],
    "overdue_primary_ids": [
        "WI-24024-036",
        "WI-24024-074",
        "WI-24024-096",
        "WI-24024-110",
        "WI-24024-119",
        "WI-24024-S041",
        "WI-24024-S042",
        "WI-24024-S044",
        "WI-24024-S046",
    ],
    "aging_bucket_counts": {
        "0-3": 1,
        "4-7": 3,
        "8-14": 5,
        "15-30": 0,
        "31+": 5,
    },
    "team_overdue_counts": [
        {"team": "Core Services", "overdue_count": 4},
        {"team": "Platform Core", "overdue_count": 5},
    ],
    "top_hotspot": {
        "team": "Core Services",
        "owner": "Priya Stone",
        "overdue_count": 2,
    },
    "duplicate_clusters": [
        {"primary_id": "WI-24024-S041", "duplicate_ids": ["WI-24024-S049"]},
        {"primary_id": "WI-24024-S042", "duplicate_ids": ["WI-24024-S050"]},
    ],
    "missing_owner_ids": [
        "WI-24024-S046",
        "WI-24024-S047",
    ],
    "breach_rate": 0.643,
}

EXPECTED_SEEDED_PRIMARY_IDS = [
    "WI-24024-S041",
    "WI-24024-S042",
    "WI-24024-S043",
    "WI-24024-S044",
    "WI-24024-S045",
    "WI-24024-S046",
    "WI-24024-S047",
    "WI-24024-S048",
]

EXPECTED_LEGACY_PRIMARY_IDS = [
    "WI-24024-036",
    "WI-24024-046",
    "WI-24024-074",
    "WI-24024-096",
    "WI-24024-110",
    "WI-24024-119",
]

NONPRIMARY_DUPLICATE_IDS = [
    "WI-24024-S049",
    "WI-24024-S050",
]

RUBRIC = [
    (
        "included_seeded_primary_set",
        2,
        "Correct seeded primary SLA population under scope, category, status, date, and duplicate rules.",
    ),
    (
        "included_legacy_primary_set",
        1,
        "Correct legacy primary SLA population under scope, category, status, date, and duplicate rules.",
    ),
    ("nonprimary_duplicates_excluded", 1, "Duplicate records are not counted in the primary SLA population."),
    ("overdue_primary_set", 3, "Correct overdue primary items using the right comparison date."),
    ("aging_bucket_counts", 2, "Correct aging bucket counts for included primary items."),
    ("team_hotspot", 2, "Correct overdue counts by team and top owner/team hotspot."),
    ("duplicate_clusters", 2, "Correct duplicate clusters reported outside the primary population."),
    ("missing_owner_ids", 2, "Correct primary included records with missing owner."),
    ("breach_rate", 2, "Correct SLA breach rate rounded to three decimals."),
]


def load_candidate(path):
    try:
        with Path(path).open("r", encoding="utf-8") as fh:
            return json.load(fh), None
    except Exception as exc:
        return None, str(exc)


def norm_str(value):
    return value.strip() if isinstance(value, str) else value


def norm_id_set(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        item = norm_str(item)
        if not isinstance(item, str):
            return None
        normalized.append(item)
    return sorted(set(normalized))


def norm_bucket_counts(value):
    keys = ["0-3", "4-7", "8-14", "15-30", "31+"]
    if not isinstance(value, dict):
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
        if raw != number and not (isinstance(raw, str) and raw.strip() == str(number)):
            return None
        out[key] = number
    return out


def norm_team_counts(value):
    if isinstance(value, dict):
        items = [{"team": team, "overdue_count": count} for team, count in value.items()]
    elif isinstance(value, list):
        items = value
    else:
        return None
    out = []
    for item in items:
        if not isinstance(item, dict):
            return None
        team = norm_str(item.get("team"))
        raw_count = item.get("overdue_count")
        if isinstance(raw_count, bool):
            return None
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            return None
        if raw_count != count and not (isinstance(raw_count, str) and raw_count.strip() == str(count)):
            return None
        if not isinstance(team, str):
            return None
        out.append({"team": team, "overdue_count": count})
    return sorted(out, key=lambda row: row["team"])


def norm_hotspot(value):
    if not isinstance(value, dict):
        return None
    team = norm_str(value.get("team"))
    owner = norm_str(value.get("owner"))
    raw_count = value.get("overdue_count")
    if isinstance(raw_count, bool):
        return None
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        return None
    if raw_count != count and not (isinstance(raw_count, str) and raw_count.strip() == str(count)):
        return None
    if not isinstance(team, str) or not isinstance(owner, str):
        return None
    return {"team": team, "owner": owner, "overdue_count": count}


def norm_clusters(value):
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if not isinstance(item, dict):
            return None
        primary_id = norm_str(item.get("primary_id"))
        duplicate_ids = norm_id_set(item.get("duplicate_ids"))
        if not isinstance(primary_id, str) or duplicate_ids is None:
            return None
        out.append({"primary_id": primary_id, "duplicate_ids": duplicate_ids})
    return sorted(out, key=lambda row: row["primary_id"])


def norm_rate(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, 3)


def check_included(answer):
    actual = norm_id_set(answer.get("included_primary_ids"))
    expected = EXPECTED["included_primary_ids"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_seeded_included(answer):
    actual_all = norm_id_set(answer.get("included_primary_ids"))
    actual = (
        None
        if actual_all is None
        else sorted(
            [item for item in actual_all if item.startswith("WI-24024-S") and item not in NONPRIMARY_DUPLICATE_IDS]
        )
    )
    expected = EXPECTED_SEEDED_PRIMARY_IDS
    return actual == expected, {"actual": actual, "expected": expected}


def check_legacy_included(answer):
    actual_all = norm_id_set(answer.get("included_primary_ids"))
    actual = None if actual_all is None else sorted([item for item in actual_all if not item.startswith("WI-24024-S")])
    expected = EXPECTED_LEGACY_PRIMARY_IDS
    return actual == expected, {"actual": actual, "expected": expected}


def check_nonprimary_duplicates_excluded(answer):
    actual_all = norm_id_set(answer.get("included_primary_ids"))
    present = None if actual_all is None else sorted(set(actual_all) & set(NONPRIMARY_DUPLICATE_IDS))
    return present == [], {"actual_present": present, "expected_absent": NONPRIMARY_DUPLICATE_IDS}


def check_overdue(answer):
    actual = norm_id_set(answer.get("overdue_primary_ids"))
    expected = EXPECTED["overdue_primary_ids"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_buckets(answer):
    actual = norm_bucket_counts(answer.get("aging_bucket_counts"))
    expected = EXPECTED["aging_bucket_counts"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_hotspot(answer):
    actual_team_counts = norm_team_counts(answer.get("team_overdue_counts"))
    actual_hotspot = norm_hotspot(answer.get("top_hotspot"))
    expected_team_counts = EXPECTED["team_overdue_counts"]
    expected_hotspot = EXPECTED["top_hotspot"]
    passed = actual_team_counts == expected_team_counts and actual_hotspot == expected_hotspot
    return passed, {
        "actual_team_overdue_counts": actual_team_counts,
        "expected_team_overdue_counts": expected_team_counts,
        "actual_top_hotspot": actual_hotspot,
        "expected_top_hotspot": expected_hotspot,
    }


def check_clusters(answer):
    actual = norm_clusters(answer.get("duplicate_clusters"))
    expected = EXPECTED["duplicate_clusters"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_missing_owner(answer):
    actual = norm_id_set(answer.get("missing_owner_ids"))
    expected = EXPECTED["missing_owner_ids"]
    return actual == expected, {"actual": actual, "expected": expected}


def check_rate(answer):
    actual = norm_rate(answer.get("breach_rate"))
    expected = EXPECTED["breach_rate"]
    return actual == expected, {"actual": actual, "expected": expected}


CHECKS = {
    "included_seeded_primary_set": check_seeded_included,
    "included_legacy_primary_set": check_legacy_included,
    "nonprimary_duplicates_excluded": check_nonprimary_duplicates_excluded,
    "overdue_primary_set": check_overdue,
    "aging_bucket_counts": check_buckets,
    "team_hotspot": check_hotspot,
    "duplicate_clusters": check_clusters,
    "missing_owner_ids": check_missing_owner,
    "breach_rate": check_rate,
}


def score(candidate):
    max_points = sum(weight for _, weight, _ in RUBRIC)
    earned = 0
    details = []
    for key, weight, description in RUBRIC:
        passed, check_details = CHECKS[key](candidate)
        if passed:
            earned += weight
        details.append(
            {
                "id": key,
                "description": description,
                "weight": weight,
                "passed": passed,
                "earned": weight if passed else 0,
                "max": weight,
                "details": check_details,
            }
        )
    return {
        "score": round(earned / max_points, 6),
        "points": earned,
        "max_score": max_points,
        "details": details,
    }


def main():
    max_points = sum(weight for _, weight, _ in RUBRIC)
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "points": 0,
                    "max_score": max_points,
                    "error": "usage: eval.py /path/to/candidate_answer.json",
                }
            )
        )
        return 0
    candidate, error = load_candidate(sys.argv[1])
    if error is not None:
        print(
            json.dumps(
                {"score": 0, "points": 0, "max_score": max_points, "error": error, "details": []}, sort_keys=True
            )
        )
        return 0
    print(json.dumps(score(candidate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
