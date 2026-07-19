#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED_INCLUDED = [
    "WI-24024-009",
    "WI-24024-012",
    "WI-24024-116",
    "WI-24024-S021",
    "WI-24024-S022",
    "WI-24024-S023",
    "WI-24024-S024",
    "WI-24024-S025",
    "WI-24024-S026",
    "WI-24024-S027",
    "WI-24024-S028",
]
EXPECTED_OVERDUE = [
    "WI-24024-116",
    "WI-24024-S021",
    "WI-24024-S022",
    "WI-24024-S024",
    "WI-24024-S026",
]
EXPECTED_SEVERITY_COUNTS = {"S1": 2, "S2": 2, "S3": 1, "S4": 0}
EXPECTED_ESCALATION = [
    "WI-24024-S021",
    "WI-24024-S026",
    "WI-24024-S024",
    "WI-24024-S022",
    "WI-24024-116",
]
EXPECTED_MISSING_OWNER = ["WI-24024-S026", "WI-24024-S027"]
EXPECTED_DUPLICATE_CLUSTERS = [
    {"primary_id": "WI-24024-S021", "duplicate_ids": ["WI-24024-S029"]},
    {"primary_id": "WI-24024-S022", "duplicate_ids": ["WI-24024-S030"]},
]
EXPECTED_BREACH_RATE = 0.455

RUBRIC = [
    ("included_primary_set", 3, "Correct included primary work item set."),
    ("overdue_primary_set", 3, "Correct overdue primary work item set."),
    ("severity_overdue_counts", 2, "Correct overdue counts by severity S1 through S4."),
    ("escalation_ordering", 2, "Correct priority order for the escalation queue."),
    ("missing_owner_ids", 1, "Correct included primary ids with missing owners."),
    ("duplicate_clusters", 1, "Correct duplicate clusters reported separately from primary work."),
    ("breach_rate", 2, "Correct SLA breach rate rounded to three decimals."),
]


def normalize_string_list(value):
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if not isinstance(item, str):
            return None
        text = item.strip()
        if text:
            out.append(text)
    return sorted(set(out))


def ordered_ids(value):
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict) and isinstance(item.get("id"), str):
            text = item["id"].strip()
        else:
            return None
        if text:
            out.append(text)
    return out


def normalize_counts(value):
    if not isinstance(value, dict):
        return None
    out = {}
    for sev in ["S1", "S2", "S3", "S4"]:
        raw = value.get(sev)
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int):
            out[sev] = raw
        elif isinstance(raw, float) and raw.is_integer():
            out[sev] = int(raw)
        elif isinstance(raw, str) and raw.strip().isdigit():
            out[sev] = int(raw.strip())
        else:
            return None
    return out


def normalize_duplicate_clusters(value):
    if not isinstance(value, list):
        return None
    clusters = []
    for item in value:
        if not isinstance(item, dict):
            return None
        primary = item.get("primary_id")
        duplicates = item.get("duplicate_ids")
        if not isinstance(primary, str):
            return None
        norm_dups = normalize_string_list(duplicates)
        if norm_dups is None:
            return None
        clusters.append({"primary_id": primary.strip(), "duplicate_ids": norm_dups})
    return sorted(clusters, key=lambda row: (row["primary_id"], row["duplicate_ids"]))


def normalize_rate(value):
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return round(numeric, 3)


def point(name, weight, description, passed, expected, actual):
    return {
        "name": name,
        "weight": weight,
        "description": description,
        "passed": bool(passed),
        "earned_raw": weight if passed else 0,
        "expected": expected,
        "actual": actual,
    }


def evaluate(candidate):
    included = normalize_string_list(candidate.get("included_primary_ids"))
    overdue = normalize_string_list(candidate.get("overdue_primary_ids"))
    counts = normalize_counts(candidate.get("overdue_counts_by_severity"))
    escalation = ordered_ids(candidate.get("escalation_queue_ids", candidate.get("escalation_queue")))
    missing = normalize_string_list(candidate.get("missing_owner_ids"))
    clusters = normalize_duplicate_clusters(candidate.get("duplicate_clusters"))
    rate = normalize_rate(candidate.get("sla_breach_rate"))

    expected_clusters = normalize_duplicate_clusters(EXPECTED_DUPLICATE_CLUSTERS)

    checks = []
    for name, weight, description in RUBRIC:
        if name == "included_primary_set":
            checks.append(point(name, weight, description, included == EXPECTED_INCLUDED, EXPECTED_INCLUDED, included))
        elif name == "overdue_primary_set":
            checks.append(point(name, weight, description, overdue == EXPECTED_OVERDUE, EXPECTED_OVERDUE, overdue))
        elif name == "severity_overdue_counts":
            checks.append(
                point(name, weight, description, counts == EXPECTED_SEVERITY_COUNTS, EXPECTED_SEVERITY_COUNTS, counts)
            )
        elif name == "escalation_ordering":
            checks.append(
                point(name, weight, description, escalation == EXPECTED_ESCALATION, EXPECTED_ESCALATION, escalation)
            )
        elif name == "missing_owner_ids":
            checks.append(
                point(name, weight, description, missing == EXPECTED_MISSING_OWNER, EXPECTED_MISSING_OWNER, missing)
            )
        elif name == "duplicate_clusters":
            checks.append(point(name, weight, description, clusters == expected_clusters, expected_clusters, clusters))
        elif name == "breach_rate":
            checks.append(point(name, weight, description, rate == EXPECTED_BREACH_RATE, EXPECTED_BREACH_RATE, rate))

    max_raw = sum(item["weight"] for item in checks)
    earned_raw = sum(item["earned_raw"] for item in checks)
    return {
        "score": round(earned_raw / max_raw, 6),
        "points": checks,
        "max_score": 1,
        "earned_raw": earned_raw,
        "max_raw": max_raw,
    }


def main():
    path = Path(sys.argv[1])
    try:
        candidate = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "points": [],
                    "max_score": 1,
                    "earned_raw": 0,
                    "max_raw": sum(weight for _, weight, _ in RUBRIC),
                    "error": f"could not parse candidate JSON: {exc}",
                },
                sort_keys=True,
            )
        )
        return
    print(json.dumps(evaluate(candidate), sort_keys=True))


if __name__ == "__main__":
    main()
