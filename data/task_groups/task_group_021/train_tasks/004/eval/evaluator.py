#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ANSWER_PATH = SCRIPT_DIR.parent / "output" / "answer.json"


SCORING_POINTS = [
    {
        "id": "campaign_id",
        "weight": 1,
        "fields": ["campaign_id"],
        "goal": "Correct target campaign identifier."
    },
    {
        "id": "qualified_reachable_count",
        "weight": 2,
        "fields": ["qualified_reachable_count"],
        "goal": "Correct unique qualified reachable audience count."
    },
    {
        "id": "blocked_or_suppressed_ids",
        "weight": 2,
        "fields": ["blocked_or_suppressed_ids"],
        "goal": "Correct hard-blocked or suppressed campaign member IDs."
    },
    {
        "id": "needs_manual_review_ids",
        "weight": 2,
        "fields": ["needs_manual_review_ids"],
        "goal": "Correct campaign member IDs requiring manual review."
    },
    {
        "id": "domain_counts",
        "weight": 1,
        "fields": ["domain_counts"],
        "goal": "Correct retained-audience email domain counts."
    },
    {
        "id": "segment_counts",
        "weight": 1,
        "fields": ["segment_counts"],
        "goal": "Correct retained-audience canonical segment counts."
    },
    {
        "id": "duplicate_person_keys",
        "weight": 2,
        "fields": ["duplicate_person_keys"],
        "goal": "Correct duplicate campaign person keys."
    },
    {
        "id": "canonical_member_sample",
        "weight": 3,
        "fields": ["canonical_member_sample"],
        "goal": "Correct canonical retained member audit sample."
    },
]

SET_LIKE_LIST_FIELDS = {
    "blocked_or_suppressed_ids",
    "needs_manual_review_ids",
    "duplicate_person_keys",
}


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def normalize_value(field: str, value):
    if field in SET_LIKE_LIST_FIELDS and isinstance(value, list):
        return sorted(str(item) for item in value)
    if field in {"domain_counts", "segment_counts"} and isinstance(value, dict):
        return {str(key): value[key] for key in sorted(value)}
    return value


def point_matches(point, expected, actual) -> bool:
    for field in point["fields"]:
        if normalize_value(field, actual.get(field)) != normalize_value(field, expected.get(field)):
            return False
    return True


def main() -> int:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ANSWER_PATH
    expected = load_json(ANSWER_PATH)
    try:
        actual = load_json(prediction_path)
    except Exception as exc:
        total = sum(point["weight"] for point in SCORING_POINTS)
        print(json.dumps({
            "score": 0,
            "max_score": total,
            "normalized_score": 0.0,
            "error": f"Could not load prediction JSON: {exc}",
            "points": []
        }, indent=2, sort_keys=True))
        return 0

    scored = []
    score = 0
    for point in SCORING_POINTS:
        matched = point_matches(point, expected, actual)
        earned = point["weight"] if matched else 0
        score += earned
        scored.append({
            "id": point["id"],
            "goal": point["goal"],
            "weight": point["weight"],
            "earned": earned,
            "matched": matched
        })

    max_score = sum(point["weight"] for point in SCORING_POINTS)
    print(json.dumps({
        "score": score,
        "max_score": max_score,
        "normalized_score": round(score / max_score, 6),
        "points": scored
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
