#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED_DECISION = "NO_SHIP"

EXPECTED_MILESTONES = [
    {
        "milestone_id": "MIL-ORION-BETA",
        "complete_primary": 2,
        "primary_total": 2,
        "completion_pct": 100.0,
    },
    {
        "milestone_id": "MIL-ORION-GA",
        "complete_primary": 4,
        "primary_total": 6,
        "completion_pct": 66.7,
    },
    {
        "milestone_id": "MIL-ORION-HARDEN",
        "complete_primary": 3,
        "primary_total": 5,
        "completion_pct": 60.0,
    },
    {
        "milestone_id": "MIL-ORION-RC",
        "complete_primary": 2,
        "primary_total": 3,
        "completion_pct": 66.7,
    },
]

EXPECTED_GATING_IDS = ["WI-24024-010", "WI-24024-012"]

EXPECTED_BLOCKER_CAUSES = {
    "open reliability rehearsal gap": 1,
    "release note evidence gap": 1,
    "unresolved cve exception": 1,
}

EXPECTED_DEPENDENCY_CHAINS = []
EXPECTED_READINESS_SCORE = 0.688


RUBRIC = [
    ("decision_enum", 3),
    ("milestone_metrics", 3),
    ("gating_set", 3),
    ("blocker_cause_counts", 2),
    ("dependency_chains", 2),
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
