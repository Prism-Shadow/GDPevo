#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    ("readiness_statuses", 2, ["referrals.*.readiness_status"]),
    ("issue_code_sets", 2, ["referrals.*.issue_codes"]),
    ("coding_outcomes", 2, ["referrals.*.coding"]),
    ("duplicate_links", 1, ["referrals.*.duplicate_linked_referral_ids"]),
    ("priority_tiers", 3, ["referrals.*.priority_tier"]),
    ("follow_up_queue", 1, ["referrals.*.follow_up_practice", "follow_up_practices"]),
    ("ready_count", 1, ["ready_count"]),
]

SET_FIELDS = {"issue_codes", "duplicate_linked_referral_ids", "follow_up_practices"}


def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(point[1] for point in POINTS),
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
        if isinstance(out.get("referrals"), list):
            out["referrals"] = sorted(out["referrals"], key=lambda item: item.get("referral_id", ""))
        return out
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def referral_map(data):
    rows = data.get("referrals")
    if not isinstance(rows, list):
        return {}
    return {item.get("referral_id"): item for item in rows if isinstance(item, dict)}


def pick(data, selector):
    if selector == "ready_count":
        return data.get("ready_count")
    if selector == "follow_up_practices":
        return data.get("follow_up_practices")
    if selector.startswith("referrals.*."):
        field = selector.split(".", 2)[2]
        return {rid: item.get(field) for rid, item in referral_map(data).items()}
    raise KeyError(selector)


def main():
    if len(sys.argv) not in {2, 3}:
        print("Usage: evaluator.py ACTUAL_JSON [EXPECTED_JSON]", file=sys.stderr)
        sys.exit(2)

    actual_path = Path(sys.argv[1])
    expected_path = (
        Path(sys.argv[2]) if len(sys.argv) == 3 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )

    expected = normalize(load_json(expected_path))
    actual = normalize(load_json(actual_path))

    score = 0
    details = []
    for name, weight, selectors in POINTS:
        expected_slice = {selector: pick(expected, selector) for selector in selectors}
        actual_slice = {selector: pick(actual, selector) for selector in selectors}
        passed = expected_slice == actual_slice
        if passed:
            score += weight
        details.append({"name": name, "points": weight, "passed": passed})

    max_score = sum(point[1] for point in POINTS)
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
