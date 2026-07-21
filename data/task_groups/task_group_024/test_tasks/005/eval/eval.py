#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED = {
    "included_primary_ids": [
        "WI-24024-010",
        "WI-24024-064",
        "WI-24024-099",
        "WI-24024-147",
        "WI-24024-S061",
        "WI-24024-S062",
        "WI-24024-S063",
        "WI-24024-S064",
        "WI-24024-S065",
        "WI-24024-S066",
        "WI-24024-S067",
        "WI-24024-S068",
    ],
    "escalation_queue_ids": [
        "WI-24024-099",
        "WI-24024-S066",
        "WI-24024-S061",
        "WI-24024-S064",
        "WI-24024-S062",
        "WI-24024-147",
    ],
    "overdue_counts_by_severity": {
        "S1": 3,
        "S2": 2,
        "S3": 0,
        "S4": 1,
    },
    "overdue_open_primary_ids": [
        "WI-24024-099",
        "WI-24024-147",
        "WI-24024-S061",
        "WI-24024-S062",
        "WI-24024-S066",
    ],
    "overdue_recently_closed_primary_ids": [
        "WI-24024-S064",
    ],
    "sla_breach_rate": 0.500,
    "duplicate_clusters": [
        {"primary_id": "WI-24024-S061", "duplicate_ids": ["WI-24024-S069"]},
        {"primary_id": "WI-24024-S062", "duplicate_ids": ["WI-24024-S070"]},
    ],
    "missing_owner_ids": [
        "WI-24024-010",
        "WI-24024-S066",
        "WI-24024-S067",
    ],
    "oldest_unowned_primary_id": "WI-24024-010",
    "top_hotspot": {
        "team": "Edge Delivery",
        "owner": "Elena Park",
        "overdue_count": 2,
    },
}

RUBRIC = [
    ("escalation_queue", 1, "Correct overdue primary ids in escalation priority order."),
    (
        "included_primary_set",
        1,
        "Correct included primary work item set under scope, category, state, date, and duplicate rules.",
    ),
    ("overdue_severity_counts", 1, "Correct overdue counts by severity S1 through S4."),
    ("overdue_open_primary_ids", 3, "Correct overdue primary records still open at the as-of date."),
    (
        "overdue_recently_closed_primary_ids",
        3,
        "Correct overdue primary records closed inside the recent closed window.",
    ),
    ("breach_rate", 1, "Correct SLA breach rate rounded to three decimals."),
    ("duplicate_clusters", 3, "Correct duplicate clusters reported separately from primary metrics."),
    ("missing_owner_ids", 3, "Correct included primary ids with missing owners."),
    ("oldest_unowned_primary_id", 3, "Correct oldest included primary record with no owner."),
    ("top_hotspot", 3, "Correct top owner/team overdue hotspot."),
]


def load_candidate(path):
    try:
        with Path(path).open("r", encoding="utf-8") as fh:
            return json.load(fh), None
    except Exception as exc:
        return None, f"could not parse candidate JSON: {exc}"


def normalize_id_set(value):
    if not isinstance(value, list):
        return None
    ids = []
    for item in value:
        if not isinstance(item, str):
            return None
        text = item.strip()
        if text:
            ids.append(text)
    return sorted(set(ids))


def normalize_ordered_ids(value):
    if not isinstance(value, list):
        return None
    ids = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            text = item["id"].strip()
        else:
            return None
        if text:
            ids.append(text)
    return ids


def normalize_counts(value):
    if not isinstance(value, dict):
        return None
    counts = {}
    for severity in ["S1", "S2", "S3", "S4"]:
        raw = value.get(severity)
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int):
            counts[severity] = raw
        elif isinstance(raw, float) and raw.is_integer():
            counts[severity] = int(raw)
        elif isinstance(raw, str) and raw.strip().isdigit():
            counts[severity] = int(raw.strip())
        else:
            return None
    return counts


def normalize_rate(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, 3)


def normalize_clusters(value):
    if not isinstance(value, list):
        return None
    clusters = []
    for item in value:
        if not isinstance(item, dict):
            return None
        primary_id = item.get("primary_id")
        duplicate_ids = normalize_id_set(item.get("duplicate_ids"))
        if not isinstance(primary_id, str) or duplicate_ids is None:
            return None
        primary_text = primary_id.strip()
        if not primary_text:
            return None
        clusters.append({"primary_id": primary_text, "duplicate_ids": duplicate_ids})
    return sorted(clusters, key=lambda row: (row["primary_id"], row["duplicate_ids"]))


def normalize_hotspot(value):
    if not isinstance(value, dict):
        return None
    team = value.get("team")
    owner = value.get("owner")
    count = value.get("overdue_count")
    if not isinstance(team, str) or not isinstance(owner, str):
        return None
    if isinstance(count, bool):
        return None
    if isinstance(count, float) and count.is_integer():
        count = int(count)
    elif isinstance(count, str) and count.strip().isdigit():
        count = int(count.strip())
    if not isinstance(count, int):
        return None
    return {"team": team.strip(), "owner": owner.strip(), "overdue_count": count}


def scoring_point(key, weight, description, passed, expected, actual):
    return {
        "id": key,
        "description": description,
        "weight": weight,
        "passed": bool(passed),
        "earned": weight if passed else 0,
        "max": weight,
        "expected": expected,
        "actual": actual,
    }


def evaluate(candidate):
    included = normalize_id_set(candidate.get("included_primary_ids"))
    escalation = normalize_ordered_ids(candidate.get("escalation_queue_ids", candidate.get("escalation_queue")))
    counts = normalize_counts(candidate.get("overdue_counts_by_severity"))
    rate = normalize_rate(candidate.get("sla_breach_rate", candidate.get("breach_rate")))
    open_overdue = normalize_id_set(candidate.get("overdue_open_primary_ids"))
    closed_overdue = normalize_id_set(candidate.get("overdue_recently_closed_primary_ids"))
    clusters = normalize_clusters(candidate.get("duplicate_clusters"))
    missing = normalize_id_set(candidate.get("missing_owner_ids"))
    oldest_unowned = candidate.get("oldest_unowned_primary_id")
    if isinstance(oldest_unowned, str):
        oldest_unowned = oldest_unowned.strip()
    hotspot = normalize_hotspot(candidate.get("top_hotspot"))

    expected_clusters = normalize_clusters(EXPECTED["duplicate_clusters"])
    checks = {
        "escalation_queue": (
            escalation == EXPECTED["escalation_queue_ids"],
            EXPECTED["escalation_queue_ids"],
            escalation,
        ),
        "included_primary_set": (
            included == EXPECTED["included_primary_ids"],
            EXPECTED["included_primary_ids"],
            included,
        ),
        "overdue_severity_counts": (
            counts == EXPECTED["overdue_counts_by_severity"],
            EXPECTED["overdue_counts_by_severity"],
            counts,
        ),
        "overdue_open_primary_ids": (
            open_overdue == EXPECTED["overdue_open_primary_ids"],
            EXPECTED["overdue_open_primary_ids"],
            open_overdue,
        ),
        "overdue_recently_closed_primary_ids": (
            closed_overdue == EXPECTED["overdue_recently_closed_primary_ids"],
            EXPECTED["overdue_recently_closed_primary_ids"],
            closed_overdue,
        ),
        "breach_rate": (
            rate == EXPECTED["sla_breach_rate"],
            EXPECTED["sla_breach_rate"],
            rate,
        ),
        "duplicate_clusters": (
            clusters == expected_clusters,
            expected_clusters,
            clusters,
        ),
        "missing_owner_ids": (
            missing == EXPECTED["missing_owner_ids"],
            EXPECTED["missing_owner_ids"],
            missing,
        ),
        "oldest_unowned_primary_id": (
            oldest_unowned == EXPECTED["oldest_unowned_primary_id"],
            EXPECTED["oldest_unowned_primary_id"],
            oldest_unowned,
        ),
        "top_hotspot": (
            hotspot == EXPECTED["top_hotspot"],
            EXPECTED["top_hotspot"],
            hotspot,
        ),
    }

    details = []
    for key, weight, description in RUBRIC:
        passed, expected, actual = checks[key]
        details.append(scoring_point(key, weight, description, passed, expected, actual))

    max_points = sum(item["weight"] for item in details)
    earned = sum(item["earned"] for item in details)
    return {
        "score": round(earned / max_points, 6),
        "points": earned,
        "max_score": max_points,
        "scoring_points": details,
    }


def main():
    if len(sys.argv) != 2:
        max_points = sum(weight for _, weight, _ in RUBRIC)
        print(
            json.dumps(
                {
                    "score": 0,
                    "points": 0,
                    "max_score": max_points,
                    "error": "usage: eval.py /path/to/candidate_answer.json",
                },
                sort_keys=True,
            )
        )
        return

    candidate, error = load_candidate(sys.argv[1])
    if error is not None:
        max_points = sum(weight for _, weight, _ in RUBRIC)
        print(
            json.dumps(
                {
                    "score": 0,
                    "points": 0,
                    "max_score": max_points,
                    "error": error,
                    "scoring_points": [],
                },
                sort_keys=True,
            )
        )
        return

    print(json.dumps(evaluate(candidate), sort_keys=True))


if __name__ == "__main__":
    main()
