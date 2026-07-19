#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED_DECISION = "NO_SHIP"

EXPECTED_MILESTONES = [
    {
        "milestone_id": "MIL-ZEPHYR-BETA",
        "complete_primary": 4,
        "primary_total": 5,
        "completion_pct": 80.0,
    },
    {
        "milestone_id": "MIL-ZEPHYR-GA",
        "complete_primary": 2,
        "primary_total": 6,
        "completion_pct": 33.3,
    },
    {
        "milestone_id": "MIL-ZEPHYR-HARDEN",
        "complete_primary": 3,
        "primary_total": 6,
        "completion_pct": 50.0,
    },
    {
        "milestone_id": "MIL-ZEPHYR-RC",
        "complete_primary": 1,
        "primary_total": 2,
        "completion_pct": 50.0,
    },
]

EXPECTED_GATING_IDS = [
    "WI-24024-017",
    "WI-24024-054",
    "WI-24024-087",
    "WI-24024-140",
]

EXPECTED_BLOCKER_CAUSES = {
    "missing encryption audit evidence": 1,
}

EXPECTED_DEPENDENCY_CHAINS = [
    ["WI-24024-054", "WI-24024-132"],
    ["WI-24024-087", "WI-24024-050"],
    ["WI-24024-140", "WI-24024-127"],
]

EXPECTED_WATCH_IDS = [
    "WI-24024-014",
    "WI-24024-032",
    "WI-24024-079",
    "WI-24024-090",
    "WI-24024-115",
]

EXPECTED_WATCH_BLOCKER_CAUSES = {
    "dependency validation late": 1,
    "owner unavailable": 1,
    "release note evidence gap": 1,
}

EXPECTED_WATCH_MILESTONES = [
    {"milestone_id": "MIL-ZEPHYR-BETA", "owner_team": "API Foundations", "watch_primary_count": 1},
    {"milestone_id": "MIL-ZEPHYR-GA", "owner_team": "Release Engineering", "watch_primary_count": 2},
    {"milestone_id": "MIL-ZEPHYR-HARDEN", "owner_team": "Data Platform", "watch_primary_count": 1},
    {"milestone_id": "MIL-ZEPHYR-RC", "owner_team": "Revenue Platform", "watch_primary_count": 1},
]
EXPECTED_READINESS_SCORE = 0.526


RUBRIC = [
    ("decision_enum", 3),
    ("milestone_metrics", 3),
    ("gating_set", 3),
    ("blocker_cause_counts", 2),
    ("dependency_chains", 2),
    ("watch_work_item_ids", 3),
    ("watch_blocker_cause_counts", 3),
    ("watch_milestone_summary", 3),
    ("readiness_score", 1),
]


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def clean_str(value):
    return str(value).strip()


def normalize_id_set(value):
    if not isinstance(value, list):
        return None
    return sorted({clean_str(item) for item in value})


def to_int(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    return number


def round_float(value, digits):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, digits)


def normalize_milestones(value):
    if not isinstance(value, list):
        return None
    rows = []
    seen = set()
    for row in value:
        if not isinstance(row, dict):
            return None
        milestone_id = clean_str(row.get("milestone_id", ""))
        if not milestone_id or milestone_id in seen:
            return None
        seen.add(milestone_id)
        complete_primary = to_int(row.get("complete_primary"))
        primary_total = to_int(row.get("primary_total"))
        completion_pct = round_float(row.get("completion_pct"), 1)
        if complete_primary is None or primary_total is None or completion_pct is None:
            return None
        rows.append(
            {
                "milestone_id": milestone_id,
                "complete_primary": complete_primary,
                "primary_total": primary_total,
                "completion_pct": completion_pct,
            }
        )
    return sorted(rows, key=lambda item: item["milestone_id"])


def normalize_cause_counts(value):
    if not isinstance(value, dict):
        return None
    normalized = {}
    for key, count in value.items():
        text = clean_str(key)
        number = to_int(count)
        if not text or number is None:
            return None
        normalized[text] = number
    return dict(sorted(normalized.items()))


def normalize_dependency_chains(value):
    if not isinstance(value, list):
        return None
    chains = []
    for path in value:
        if not isinstance(path, list):
            return None
        normalized_path = [clean_str(item) for item in path]
        if not normalized_path or any(not item for item in normalized_path):
            return None
        chains.append(normalized_path)
    return sorted(chains)


def normalize_watch_milestones(value):
    if not isinstance(value, list):
        return None
    rows = []
    seen = set()
    for row in value:
        if not isinstance(row, dict):
            return None
        milestone_id = clean_str(row.get("milestone_id", ""))
        owner_team = clean_str(row.get("owner_team", ""))
        count = to_int(row.get("watch_primary_count"))
        if not milestone_id or not owner_team or count is None or milestone_id in seen:
            return None
        seen.add(milestone_id)
        rows.append(
            {
                "milestone_id": milestone_id,
                "owner_team": owner_team,
                "watch_primary_count": count,
            }
        )
    return sorted(rows, key=lambda item: item["milestone_id"])


def point(name, weight, passed, details):
    return {
        "name": name,
        "weight": weight,
        "passed": bool(passed),
        "earned_points": weight if passed else 0,
        "details": details,
    }


def evaluate(candidate):
    decision = clean_str(candidate.get("ship_decision", "")).upper()
    milestones = normalize_milestones(candidate.get("milestone_completion"))
    gating_ids = normalize_id_set(candidate.get("gating_work_item_ids"))
    cause_counts = normalize_cause_counts(candidate.get("blocker_cause_counts"))
    chains = normalize_dependency_chains(candidate.get("critical_dependency_chains"))
    watch_ids = normalize_id_set(candidate.get("watch_work_item_ids"))
    watch_causes = normalize_cause_counts(candidate.get("watch_blocker_cause_counts"))
    watch_milestones = normalize_watch_milestones(candidate.get("watch_milestone_summary"))
    readiness = round_float(candidate.get("readiness_score"), 3)

    results = []
    results.append(
        point(
            "decision_enum",
            3,
            decision == EXPECTED_DECISION,
            {"expected": EXPECTED_DECISION, "actual": decision},
        )
    )
    results.append(
        point(
            "milestone_metrics",
            3,
            milestones == EXPECTED_MILESTONES,
            {"expected": EXPECTED_MILESTONES, "actual": milestones},
        )
    )
    results.append(
        point(
            "gating_set",
            3,
            gating_ids == EXPECTED_GATING_IDS,
            {"expected": EXPECTED_GATING_IDS, "actual": gating_ids},
        )
    )
    results.append(
        point(
            "blocker_cause_counts",
            2,
            cause_counts == EXPECTED_BLOCKER_CAUSES,
            {"expected": EXPECTED_BLOCKER_CAUSES, "actual": cause_counts},
        )
    )
    results.append(
        point(
            "dependency_chains",
            2,
            chains == EXPECTED_DEPENDENCY_CHAINS,
            {"expected": EXPECTED_DEPENDENCY_CHAINS, "actual": chains},
        )
    )
    results.append(
        point(
            "watch_work_item_ids",
            3,
            watch_ids == EXPECTED_WATCH_IDS,
            {"expected": EXPECTED_WATCH_IDS, "actual": watch_ids},
        )
    )
    results.append(
        point(
            "watch_blocker_cause_counts",
            3,
            watch_causes == EXPECTED_WATCH_BLOCKER_CAUSES,
            {"expected": EXPECTED_WATCH_BLOCKER_CAUSES, "actual": watch_causes},
        )
    )
    results.append(
        point(
            "watch_milestone_summary",
            3,
            watch_milestones == EXPECTED_WATCH_MILESTONES,
            {"expected": EXPECTED_WATCH_MILESTONES, "actual": watch_milestones},
        )
    )
    results.append(
        point(
            "readiness_score",
            1,
            readiness == EXPECTED_READINESS_SCORE,
            {"expected": EXPECTED_READINESS_SCORE, "actual": readiness},
        )
    )
    return results


def main():
    max_points = sum(weight for _, weight in RUBRIC)
    try:
        if len(sys.argv) < 2:
            raise ValueError("usage: eval.py <candidate-answer.json>")
        candidate = load_json(sys.argv[1])
        if not isinstance(candidate, dict):
            raise ValueError("candidate answer must be a JSON object")
        results = evaluate(candidate)
        earned = sum(item["earned_points"] for item in results)
        payload = {
            "score": round(earned / max_points, 6),
            "points": earned,
            "max_score": max_points,
            "details": results,
        }
    except Exception as exc:
        payload = {
            "score": 0,
            "points": 0,
            "max_score": max_points,
            "error": str(exc),
            "details": [],
        }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
