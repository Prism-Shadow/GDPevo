#!/usr/bin/env python3
import json
import sys
from pathlib import Path


BOUNDARY_DATE = "2025-04-10"

EXPECTED_QUEUE = [
    {
        "rank": 1,
        "license_no": "AL-TR3-007",
        "facility_name": "Train 003 Facility 07",
        "violation_count": 3,
        "most_recent_violation_date": "2025-04-05",
        "matched_violation_ids": [
            "AV-AL-TR3-007-1",
            "AV-AL-TR3-007-3",
            "AV-AL-TR3-007-2",
        ],
        "match_confidence": "exact",
        "risk_tier": "high",
        "next_step_label": "board_review",
    },
    {
        "rank": 2,
        "license_no": "AL-TR3-006",
        "facility_name": "Train 003 Facility 06",
        "violation_count": 3,
        "most_recent_violation_date": "2025-03-30",
        "matched_violation_ids": [
            "AV-AL-TR3-006-1",
            "AV-AL-TR3-OLD-006-S2",
            "AV-AL-TR3-OLD-006-S1",
        ],
        "match_confidence": "close_address",
        "risk_tier": "high",
        "next_step_label": "board_review",
    },
    {
        "rank": 3,
        "license_no": "AL-TR3-008",
        "facility_name": "Train 003 Facility 08",
        "violation_count": 4,
        "most_recent_violation_date": "2025-02-21",
        "matched_violation_ids": [
            "AV-AL-TR3-008-1",
            "AV-AL-TR3-008-3",
            "AV-AL-TR3-008-2",
            "AV-AL-TR3-008-4",
        ],
        "match_confidence": "exact",
        "risk_tier": "high",
        "next_step_label": "board_review",
    },
    {
        "rank": 4,
        "license_no": "AL-TR3-002",
        "facility_name": "Train 003 Facility 02",
        "violation_count": 4,
        "most_recent_violation_date": "2025-03-31",
        "matched_violation_ids": [
            "AV-AL-TR3-002-2",
            "AV-AL-TR3-002-3",
            "AV-AL-TR3-002-4",
            "AV-AL-TR3-002-1",
        ],
        "match_confidence": "exact",
        "risk_tier": "high",
        "next_step_label": "manual_fine_check",
    },
    {
        "rank": 5,
        "license_no": "AL-TR3-005",
        "facility_name": "Train 003 Facility 05",
        "violation_count": 4,
        "most_recent_violation_date": "2025-03-26",
        "matched_violation_ids": [
            "AV-AL-TR3-005-3",
            "AV-AL-TR3-005-4",
            "AV-AL-TR3-005-1",
            "AV-AL-TR3-005-2",
        ],
        "match_confidence": "exact",
        "risk_tier": "high",
        "next_step_label": "manual_fine_check",
    },
    {
        "rank": 6,
        "license_no": "AL-TR3-009",
        "facility_name": "Train 003 Facility 09",
        "violation_count": 2,
        "most_recent_violation_date": "2024-12-28",
        "matched_violation_ids": [
            "AV-AL-TR3-009-1",
            "AV-AL-TR3-009-2",
        ],
        "match_confidence": "exact",
        "risk_tier": "high",
        "next_step_label": "manual_fine_check",
    },
    {
        "rank": 7,
        "license_no": "AL-TR3-004",
        "facility_name": "Train 003 Facility 04",
        "violation_count": 3,
        "most_recent_violation_date": "2024-12-25",
        "matched_violation_ids": [
            "AV-AL-TR3-004-1",
            "AV-AL-TR3-004-3",
            "AV-AL-TR3-004-2",
        ],
        "match_confidence": "exact",
        "risk_tier": "high",
        "next_step_label": "manual_fine_check",
    },
    {
        "rank": 8,
        "license_no": "AL-TR3-010",
        "facility_name": "Train 003 Facility 10",
        "violation_count": 3,
        "most_recent_violation_date": "2025-03-06",
        "matched_violation_ids": [
            "AV-AL-TR3-010-2",
            "AV-AL-TR3-010-1",
            "AV-AL-TR3-010-3",
        ],
        "match_confidence": "exact",
        "risk_tier": "high",
        "next_step_label": "manual_ALERT_check",
    },
    {
        "rank": 9,
        "license_no": "AL-TR3-003",
        "facility_name": "Train 003 Facility 03",
        "violation_count": 2,
        "most_recent_violation_date": "2025-02-09",
        "matched_violation_ids": [
            "AV-AL-TR3-003-2",
            "AV-AL-TR3-003-1",
        ],
        "match_confidence": "exact",
        "risk_tier": "high",
        "next_step_label": "manual_ALERT_check",
    },
    {
        "rank": 10,
        "license_no": "AL-TR3-001",
        "facility_name": "Train 003 Facility 01",
        "violation_count": 3,
        "most_recent_violation_date": "2024-12-24",
        "matched_violation_ids": [
            "AV-AL-TR3-001-3",
            "AV-AL-TR3-001-1",
            "AV-AL-TR3-001-2",
        ],
        "match_confidence": "exact",
        "risk_tier": "medium",
        "next_step_label": "manual_ALERT_check",
    },
]

EXPECTED_BY_LICENSE = {entry["license_no"]: entry for entry in EXPECTED_QUEUE}
EXPECTED_ORDER = [entry["license_no"] for entry in EXPECTED_QUEUE]
EXPECTED_POST_BOUNDARY_IDS = [
    "AV-AL-TR3-001-LATE",
    "AV-AL-TR3-002-LATE",
    "AV-AL-TR3-003-LATE",
    "AV-AL-TR3-004-LATE",
    "AV-AL-TR3-005-LATE",
    "AV-AL-TR3-006-LATE",
    "AV-AL-TR3-007-LATE",
    "AV-AL-TR3-008-LATE",
    "AV-AL-TR3-009-LATE",
    "AV-AL-TR3-010-LATE",
]
EXPECTED_CLOSE_OR_UNCERTAIN = ["AL-TR3-006"]
EXPECTED_BOARD_REVIEW = ["AL-TR3-006", "AL-TR3-007", "AL-TR3-008"]


def load_json(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:  # noqa: BLE001 - evaluator should report all load errors as data.
        return None, f"Could not load candidate JSON: {exc}"


def as_list(value):
    return value if isinstance(value, list) else []


def as_dict(value):
    return value if isinstance(value, dict) else {}


def normalize_string(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_set(value):
    return sorted(normalize_string(item) for item in as_list(value))


def queue_sorted_by_rank(candidate):
    entries = as_list(as_dict(candidate).get("queue"))
    return sorted(
        entries,
        key=lambda item: (
            normalize_int(as_dict(item).get("rank")) is None,
            normalize_int(as_dict(item).get("rank")) or 9999,
        ),
    )


def candidate_by_license(candidate):
    result = {}
    for entry in as_list(as_dict(candidate).get("queue")):
        entry = as_dict(entry)
        license_no = normalize_string(entry.get("license_no"))
        if license_no:
            result[license_no] = entry
    return result


def check_order(candidate):
    entries = queue_sorted_by_rank(candidate)
    ranks = [normalize_int(as_dict(entry).get("rank")) for entry in entries]
    order = [normalize_string(as_dict(entry).get("license_no")) for entry in entries]
    expected_ranks = list(range(1, 11))
    passed = ranks == expected_ranks and order == EXPECTED_ORDER
    return (
        passed,
        f"Expected rank/license order {list(zip(expected_ranks, EXPECTED_ORDER))}; got {list(zip(ranks, order))}.",
    )


def check_matched_violation_ids(candidate):
    by_license = candidate_by_license(candidate)
    mismatches = []
    for license_no, expected in EXPECTED_BY_LICENSE.items():
        got_ids = normalize_set(as_dict(by_license.get(license_no)).get("matched_violation_ids"))
        expected_ids = normalize_set(expected["matched_violation_ids"])
        if got_ids != expected_ids:
            mismatches.append({"license_no": license_no, "expected": expected_ids, "got": got_ids})
    passed = not mismatches
    details = "All matched violation ID sets matched, including the AL-TR3-006 successor rows."
    if not passed:
        details = f"Mismatches: {mismatches}"
    return passed, details


def check_counts_and_dates(candidate):
    by_license = candidate_by_license(candidate)
    mismatches = []
    for license_no, expected in EXPECTED_BY_LICENSE.items():
        entry = as_dict(by_license.get(license_no))
        count = normalize_int(entry.get("violation_count"))
        recent_date = normalize_string(entry.get("most_recent_violation_date"))
        if count != expected["violation_count"] or recent_date != expected["most_recent_violation_date"]:
            mismatches.append(
                {
                    "license_no": license_no,
                    "expected": [expected["violation_count"], expected["most_recent_violation_date"]],
                    "got": [count, recent_date],
                }
            )
    passed = not mismatches
    return passed, "All counts and most recent dates matched." if passed else f"Mismatches: {mismatches}"


def check_match_confidence(candidate):
    by_license = candidate_by_license(candidate)
    summary = as_dict(as_dict(candidate).get("summary"))
    mismatches = []
    for license_no, expected in EXPECTED_BY_LICENSE.items():
        got = normalize_string(as_dict(by_license.get(license_no)).get("match_confidence"))
        if got != expected["match_confidence"]:
            mismatches.append({"license_no": license_no, "expected": expected["match_confidence"], "got": got})
    got_summary = normalize_set(summary.get("close_or_uncertain_match_license_numbers"))
    passed = not mismatches and got_summary == EXPECTED_CLOSE_OR_UNCERTAIN
    details = "All match confidences and close/uncertain summary matched."
    if not passed:
        details = f"Entry mismatches: {mismatches}; expected close/uncertain {EXPECTED_CLOSE_OR_UNCERTAIN}, got {got_summary}."
    return passed, details


def check_next_steps(candidate):
    by_license = candidate_by_license(candidate)
    mismatches = []
    for license_no, expected in EXPECTED_BY_LICENSE.items():
        got = normalize_string(as_dict(by_license.get(license_no)).get("next_step_label"))
        if got != expected["next_step_label"]:
            mismatches.append({"license_no": license_no, "expected": expected["next_step_label"], "got": got})
    passed = not mismatches
    return passed, "All next-step labels matched." if passed else f"Mismatches: {mismatches}"


def check_boundary_exclusions(candidate):
    summary = as_dict(as_dict(candidate).get("summary"))
    got_ids = normalize_set(summary.get("post_boundary_violation_ids_excluded"))
    entries = as_list(as_dict(candidate).get("queue"))
    late_dates = [
        normalize_string(as_dict(entry).get("most_recent_violation_date"))
        for entry in entries
        if normalize_string(as_dict(entry).get("most_recent_violation_date")) > BOUNDARY_DATE
    ]
    passed = got_ids == EXPECTED_POST_BOUNDARY_IDS and not late_dates
    details = "Post-boundary exclusions and used dates matched."
    if not passed:
        details = f"Expected excluded ids {EXPECTED_POST_BOUNDARY_IDS}, got {got_ids}; late used dates: {late_dates}."
    return passed, details


def check_risk_tiers_and_board_set(candidate):
    by_license = candidate_by_license(candidate)
    summary = as_dict(as_dict(candidate).get("summary"))
    mismatches = []
    for license_no, expected in EXPECTED_BY_LICENSE.items():
        got = normalize_string(as_dict(by_license.get(license_no)).get("risk_tier"))
        if got != expected["risk_tier"]:
            mismatches.append({"license_no": license_no, "expected": expected["risk_tier"], "got": got})
    got_board = normalize_set(summary.get("board_review_license_numbers"))
    passed = not mismatches and got_board == EXPECTED_BOARD_REVIEW
    details = "Risk tiers and board-review summary matched."
    if not passed:
        details = f"Risk tier mismatches: {mismatches}; expected board set {EXPECTED_BOARD_REVIEW}, got {got_board}."
    return passed, details


def check_summary_and_names(candidate):
    summary = as_dict(as_dict(candidate).get("summary"))
    by_license = candidate_by_license(candidate)
    name_mismatches = []
    for license_no, expected in EXPECTED_BY_LICENSE.items():
        got = normalize_string(as_dict(by_license.get(license_no)).get("facility_name"))
        if got != expected["facility_name"]:
            name_mismatches.append({"license_no": license_no, "expected": expected["facility_name"], "got": got})
    queue_size = normalize_int(summary.get("queue_size"))
    boundary = normalize_string(summary.get("boundary_date"))
    passed = queue_size == 10 and boundary == BOUNDARY_DATE and not name_mismatches
    details = "Queue size, boundary date, and facility names matched."
    if not passed:
        details = f"Expected queue_size 10 and boundary {BOUNDARY_DATE}; got {queue_size} and {boundary}; name mismatches: {name_mismatches}."
    return passed, details


POINTS = [
    ("SP001", "Correct queue membership and exact rank order.", 3, check_order),
    (
        "SP002",
        "Correct matched violation evidence sets, including successor evidence.",
        3,
        check_matched_violation_ids,
    ),
    ("SP003", "Correct pre-boundary violation counts and most recent dates.", 2, check_counts_and_dates),
    ("SP004", "Correct match confidence classifications and close-match summary.", 2, check_match_confidence),
    ("SP005", "Correct controlled next-step labels.", 2, check_next_steps),
    ("SP006", "Correct exclusion of post-boundary violations.", 2, check_boundary_exclusions),
    ("SP007", "Correct risk tiers and board-review set.", 2, check_risk_tiers_and_board_set),
    ("SP008", "Correct queue summary and facility identity fields.", 1, check_summary_and_names),
]


def main():
    candidate_path = (
        sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    )
    candidate, load_error = load_json(candidate_path)
    if load_error:
        candidate = {}

    total_weight = sum(point[2] for point in POINTS)
    point_results = []
    total_score = 0.0
    for point_id, goal, weight, checker in POINTS:
        assigned_score = weight / total_weight
        if load_error:
            passed = False
            details = load_error
        else:
            passed, details = checker(candidate)
        earned_score = assigned_score if passed else 0.0
        total_score += earned_score
        point_results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": round(assigned_score, 6),
                "passed": bool(passed),
                "earned_score": round(earned_score, 6),
                "details": details,
            }
        )

    print(json.dumps({"score": round(total_score, 6), "points": point_results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
