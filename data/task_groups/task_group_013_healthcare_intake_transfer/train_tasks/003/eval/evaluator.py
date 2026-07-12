#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    ("task metadata", 1, ["task_id", "review_date"]),
    ("readiness statuses", 3, ["referrals.*.readiness_status"]),
    ("issue code sets", 3, ["referrals.*.issue_codes"]),
    ("coding outcomes", 2, ["referrals.*.coding"]),
    ("duplicate links", 2, ["referrals.*.duplicate_linked_referral_ids"]),
    ("priority tiers", 2, ["referrals.*.priority_tier"]),
    (
        "ready count and follow-up practices",
        1,
        ["ready_count", "follow_up_practices", "referrals.*.follow_up_practice"],
    ),
]

SET_FIELDS = {"issue_codes", "duplicate_linked_referral_ids", "follow_up_practices"}


def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(p[1] for p in POINTS),
                    "passed": False,
                    "error": f"Could not read JSON from {path}: {exc}",
                },
                indent=2,
            )
        )
        sys.exit(1)


def normalize(value):
    if isinstance(value, dict):
        out = {}
        for key, child in value.items():
            normalized = normalize(child)
            if key in SET_FIELDS and isinstance(normalized, list):
                normalized = sorted(normalized)
            out[key] = normalized
        if "referrals" in out and isinstance(out["referrals"], list):
            out["referrals"] = sorted(out["referrals"], key=lambda item: item.get("referral_id", ""))
        return out
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def referral_map(data):
    return {item.get("referral_id"): item for item in data.get("referrals", [])}


def pick(data, selector):
    if selector == "task_id":
        return data.get("task_id")
    if selector == "review_date":
        return data.get("review_date")
    if selector == "ready_count":
        return data.get("ready_count")
    if selector == "follow_up_practices":
        return data.get("follow_up_practices")
    if selector.startswith("referrals.*."):
        field = selector.split(".", 2)[2]
        return {rid: item.get(field) for rid, item in referral_map(data).items()}
    raise KeyError(selector)


def main():
    if len(sys.argv) != 3:
        print("Usage: evaluator.py EXPECTED_JSON ACTUAL_JSON", file=sys.stderr)
        sys.exit(2)

    expected = normalize(load_json(Path(sys.argv[1])))
    actual = normalize(load_json(Path(sys.argv[2])))

    score = 0
    details = []
    for name, weight, selectors in POINTS:
        expected_slice = {selector: pick(expected, selector) for selector in selectors}
        actual_slice = {selector: pick(actual, selector) for selector in selectors}
        passed = expected_slice == actual_slice
        if passed:
            score += weight
        details.append(
            {
                "name": name,
                "points": weight,
                "passed": passed,
            }
        )

    max_score = sum(p[1] for p in POINTS)
    result = {
        "score": score,
        "max_score": max_score,
        "passed": score == max_score,
        "details": details,
    }
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
