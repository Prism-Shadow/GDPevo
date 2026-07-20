#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TARGET_IDS = [f"C-TE1-{idx:03d}" for idx in range(1, 10)]

EXPECTED_DECISIONS = {
    "C-TE1-001": {
        "determination": "HOLD",
        "deficiency_codes": ["bond_not_current", "endorsement_missing", "experience_shortfall"],
        "required_actions": ["obtain_current_bond", "obtain_required_endorsement", "submit_experience_affidavit"],
        "risk_tier": "medium",
        "policy_impacted": False,
    },
    "C-TE1-002": {
        "determination": "DENY",
        "deficiency_codes": ["endorsement_pending", "insurance_shortfall", "open_serious_violation"],
        "required_actions": ["obtain_required_endorsement", "provide_current_insurance", "refer_board_discipline"],
        "risk_tier": "high",
        "policy_impacted": False,
    },
    "C-TE1-003": {
        "determination": "APPROVE",
        "deficiency_codes": [],
        "required_actions": [],
        "risk_tier": "medium",
        "policy_impacted": False,
    },
    "C-TE1-004": {
        "determination": "HOLD",
        "deficiency_codes": [
            "bond_shortfall",
            "endorsement_missing",
            "open_nonserious_violation",
            "site_recheck_required",
        ],
        "required_actions": [
            "complete_site_recheck",
            "increase_bond",
            "obtain_required_endorsement",
            "resolve_open_complaints",
        ],
        "risk_tier": "high",
        "policy_impacted": True,
    },
    "C-TE1-005": {
        "determination": "HOLD",
        "deficiency_codes": ["experience_shortfall", "insurance_expired"],
        "required_actions": ["provide_current_insurance", "submit_experience_affidavit"],
        "risk_tier": "medium",
        "policy_impacted": False,
    },
    "C-TE1-006": {
        "determination": "HOLD",
        "deficiency_codes": ["experience_shortfall", "insurance_pending", "site_recheck_required"],
        "required_actions": [
            "complete_site_recheck",
            "submit_experience_affidavit",
            "verify_current_insurance",
        ],
        "risk_tier": "medium",
        "policy_impacted": False,
    },
    "C-TE1-007": {
        "determination": "HOLD",
        "deficiency_codes": ["bond_not_current", "endorsement_missing"],
        "required_actions": ["obtain_current_bond", "obtain_required_endorsement"],
        "risk_tier": "medium",
        "policy_impacted": False,
    },
    "C-TE1-008": {
        "determination": "DENY",
        "deficiency_codes": [
            "endorsement_pending",
            "insurance_shortfall",
            "open_serious_violation",
            "site_recheck_required",
        ],
        "required_actions": [
            "complete_site_recheck",
            "obtain_required_endorsement",
            "provide_current_insurance",
            "refer_board_discipline",
        ],
        "risk_tier": "high",
        "policy_impacted": False,
    },
    "C-TE1-009": {
        "determination": "APPROVE",
        "deficiency_codes": [],
        "required_actions": [],
        "risk_tier": "medium",
        "policy_impacted": False,
    },
}

EXPECTED_SUMMARY = {
    "approve_count": 2,
    "hold_count": 5,
    "deny_count": 2,
    "high_risk_application_ids": ["C-TE1-002", "C-TE1-004", "C-TE1-008"],
    "policy_impacted_application_ids": ["C-TE1-004"],
    "stale_or_unverified_correspondence_ids": [
        "COR-C-TE1-001-1",
        "COR-C-TE1-002-1",
        "COR-C-TE1-004-1",
        "COR-C-TE1-007-1",
        "COR-C-TE1-008-1",
        "COR-DIS-0112",
    ],
}


def load_json(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def normalize_string(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    return None


def normalize_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_set(value):
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        if not isinstance(item, str):
            return None
        result.append(item.strip())
    return sorted(set(result))


def decisions_by_id(candidate):
    result = {}
    for entry in as_list(as_dict(candidate).get("application_decisions")):
        entry = as_dict(entry)
        application_id = normalize_string(entry.get("application_id"))
        if application_id:
            result[application_id] = entry
    return result


def check_application_coverage(candidate):
    entries = as_list(as_dict(candidate).get("application_decisions"))
    ids_in_order = [normalize_string(as_dict(entry).get("application_id")) for entry in entries]
    ids_sorted = sorted(ids_in_order)
    passed = ids_in_order == TARGET_IDS and ids_sorted == TARGET_IDS and len(ids_in_order) == len(set(ids_in_order))
    detail = f"expected ordered ids {TARGET_IDS}; got {ids_in_order}"
    return passed, detail


def check_determinations(candidate):
    by_id = decisions_by_id(candidate)
    mismatches = []
    for app_id in TARGET_IDS:
        actual = normalize_string(as_dict(by_id.get(app_id)).get("determination"))
        expected = EXPECTED_DECISIONS[app_id]["determination"]
        if actual != expected:
            mismatches.append({"application_id": app_id, "expected": expected, "got": actual})
    return not mismatches, "All determinations matched." if not mismatches else f"Mismatches: {mismatches}"


def check_code_sets(candidate, field):
    by_id = decisions_by_id(candidate)
    mismatches = []
    for app_id in TARGET_IDS:
        actual = normalize_set(as_dict(by_id.get(app_id)).get(field))
        expected = sorted(EXPECTED_DECISIONS[app_id][field])
        if actual != expected:
            mismatches.append({"application_id": app_id, "expected": expected, "got": actual})
    return not mismatches, f"All {field} sets matched." if not mismatches else f"Mismatches: {mismatches}"


def check_risk_tiers(candidate):
    by_id = decisions_by_id(candidate)
    summary = as_dict(as_dict(candidate).get("summary"))
    mismatches = []
    for app_id in TARGET_IDS:
        actual = normalize_string(as_dict(by_id.get(app_id)).get("risk_tier"))
        expected = EXPECTED_DECISIONS[app_id]["risk_tier"]
        if actual != expected:
            mismatches.append({"application_id": app_id, "expected": expected, "got": actual})
    actual_high = normalize_set(summary.get("high_risk_application_ids"))
    expected_high = EXPECTED_SUMMARY["high_risk_application_ids"]
    passed = not mismatches and actual_high == expected_high
    details = "Risk tiers and high-risk summary matched."
    if not passed:
        details = f"Risk tier mismatches: {mismatches}; expected high-risk ids {expected_high}, got {actual_high}."
    return passed, details


def check_policy_impacts(candidate):
    by_id = decisions_by_id(candidate)
    summary = as_dict(as_dict(candidate).get("summary"))
    mismatches = []
    for app_id in TARGET_IDS:
        actual = normalize_bool(as_dict(by_id.get(app_id)).get("policy_impacted"))
        expected = EXPECTED_DECISIONS[app_id]["policy_impacted"]
        if actual is not expected:
            mismatches.append({"application_id": app_id, "expected": expected, "got": actual})
    actual_ids = normalize_set(summary.get("policy_impacted_application_ids"))
    expected_ids = EXPECTED_SUMMARY["policy_impacted_application_ids"]
    passed = not mismatches and actual_ids == expected_ids
    details = "Policy impact flags and summary matched."
    if not passed:
        details = f"Policy flag mismatches: {mismatches}; expected policy ids {expected_ids}, got {actual_ids}."
    return passed, details


def check_summary_counts(candidate):
    summary = as_dict(as_dict(candidate).get("summary"))
    expected = {
        "approve_count": EXPECTED_SUMMARY["approve_count"],
        "hold_count": EXPECTED_SUMMARY["hold_count"],
        "deny_count": EXPECTED_SUMMARY["deny_count"],
    }
    actual = {field: normalize_int(summary.get(field)) for field in expected}
    passed = actual == expected
    return passed, f"expected counts {expected}; got {actual}"


def check_correspondence(candidate):
    summary = as_dict(as_dict(candidate).get("summary"))
    actual = normalize_set(summary.get("stale_or_unverified_correspondence_ids"))
    expected = EXPECTED_SUMMARY["stale_or_unverified_correspondence_ids"]
    passed = actual == expected
    return passed, f"expected stale/unverified correspondence ids {expected}; got {actual}"


POINTS = [
    ("SP001", "Correct application coverage and required decision ordering.", 1, check_application_coverage),
    ("SP002", "Correct approve, hold, or deny determination for every target application.", 3, check_determinations),
    (
        "SP003",
        "Correct complete deficiency-code sets for every target application.",
        3,
        lambda candidate: check_code_sets(candidate, "deficiency_codes"),
    ),
    (
        "SP004",
        "Correct required staff action-code sets for every target application.",
        2,
        lambda candidate: check_code_sets(candidate, "required_actions"),
    ),
    ("SP005", "Correct risk tiers and high-risk application summary.", 2, check_risk_tiers),
    ("SP006", "Correct current-policy impact flags and summary set.", 2, check_policy_impacts),
    ("SP007", "Correct approve, hold, and deny batch counts.", 2, check_summary_counts),
    ("SP008", "Correct stale or unverified correspondence exclusion summary.", 1, check_correspondence),
]


def main():
    script_dir = Path(__file__).resolve().parent
    default_candidate = script_dir.parent / "output" / "answer.json"
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_candidate
    candidate, load_error = load_json(candidate_path)
    if load_error:
        candidate = {}

    total_weight = sum(point[2] for point in POINTS)
    results = []
    total_score = 0.0

    for point_id, goal, weight, checker in POINTS:
        assigned_score = weight / total_weight
        if load_error:
            passed = False
            details = f"candidate JSON could not be read: {load_error}"
        elif not isinstance(candidate, dict):
            passed = False
            details = "candidate root is not a JSON object"
        else:
            passed, details = checker(candidate)
        earned_score = assigned_score if passed else 0.0
        total_score += earned_score
        results.append(
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

    print(json.dumps({"score": round(total_score, 6), "points": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
