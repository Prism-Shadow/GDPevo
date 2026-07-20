#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TARGET_IDS = [
    "C-TR4-001",
    "C-TR4-002",
    "C-TR4-003",
    "C-TR4-004",
    "C-TR4-005",
    "C-TR4-006",
    "C-TR4-007",
]

EXPECTED_DETERMINATIONS = {
    "C-TR4-001": "HOLD",
    "C-TR4-002": "HOLD",
    "C-TR4-003": "DENY",
    "C-TR4-004": "APPROVE",
    "C-TR4-005": "HOLD",
    "C-TR4-006": "HOLD",
    "C-TR4-007": "DENY",
}

EXPECTED_DEFICIENCIES = {
    "C-TR4-001": {"insurance_not_current"},
    "C-TR4-002": {"endorsement_not_verified", "experience_shortfall", "no_active_bond"},
    "C-TR4-003": {
        "endorsement_not_verified",
        "experience_shortfall",
        "insurance_shortfall",
        "unresolved_serious_complaint",
    },
    "C-TR4-004": set(),
    "C-TR4-005": {"bond_shortfall", "endorsement_not_verified"},
    "C-TR4-006": {"endorsement_not_verified", "insurance_expired"},
    "C-TR4-007": {"active_suspension", "experience_shortfall", "insurance_not_current"},
}

EXPECTED_ACTIONS = {
    "C-TR4-001": {"provide_current_insurance"},
    "C-TR4-002": {"document_experience", "file_active_bond", "verify_endorsement"},
    "C-TR4-003": {
        "board_review",
        "document_experience",
        "increase_insurance",
        "resolve_complaint",
        "verify_endorsement",
    },
    "C-TR4-004": set(),
    "C-TR4-005": {"increase_bond", "verify_endorsement"},
    "C-TR4-006": {"renew_insurance", "verify_endorsement"},
    "C-TR4-007": {
        "board_review",
        "clear_suspension",
        "document_experience",
        "provide_current_insurance",
    },
}

EXPECTED_RISK_TIERS = {
    "C-TR4-001": "medium",
    "C-TR4-002": "medium",
    "C-TR4-003": "high",
    "C-TR4-004": "low",
    "C-TR4-005": "medium",
    "C-TR4-006": "medium",
    "C-TR4-007": "high",
}

EXPECTED_POLICY_IMPACTED = {
    "C-TR4-001": False,
    "C-TR4-002": True,
    "C-TR4-003": True,
    "C-TR4-004": False,
    "C-TR4-005": True,
    "C-TR4-006": True,
    "C-TR4-007": False,
}

EXPECTED_COUNTS = {
    "approve_count": 1,
    "hold_count": 4,
    "deny_count": 2,
}

EXPECTED_HIGH_RISK = {"C-TR4-003", "C-TR4-007"}
EXPECTED_POLICY_IDS = {"C-TR4-002", "C-TR4-003", "C-TR4-005", "C-TR4-006"}
EXPECTED_CORRESPONDENCE = {
    "COR-C-TR4-002-1",
    "COR-C-TR4-005-1",
    "COR-DIS-0114",
    "COR-DIS-0117",
}

FINANCIAL_CODES = {
    "no_active_bond",
    "bond_shortfall",
    "insurance_not_current",
    "insurance_expired",
    "insurance_shortfall",
}
FINANCIAL_ACTIONS = {
    "file_active_bond",
    "increase_bond",
    "provide_current_insurance",
    "renew_insurance",
    "increase_insurance",
}
QUALIFICATION_CODES = {"endorsement_not_verified", "experience_shortfall"}
QUALIFICATION_ACTIONS = {"verify_endorsement", "document_experience"}
ENFORCEMENT_CODES = {"active_suspension", "unresolved_serious_complaint"}
ENFORCEMENT_ACTIONS = {"clear_suspension", "resolve_complaint", "board_review"}


def load_candidate(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, f"Unable to read valid JSON: {exc}"


def as_set(value):
    if not isinstance(value, list):
        return None
    return {str(item) for item in value}


def decision_map(answer):
    items = answer.get("application_decisions") if isinstance(answer, dict) else None
    if not isinstance(items, list):
        return {}, "application_decisions is not a list"
    mapped = {}
    duplicates = []
    for item in items:
        if not isinstance(item, dict):
            continue
        app_id = item.get("application_id")
        if app_id in mapped:
            duplicates.append(app_id)
        mapped[app_id] = item
    if duplicates:
        return mapped, f"duplicate application ids: {sorted(set(duplicates))}"
    return mapped, None


def summary(answer):
    value = answer.get("summary") if isinstance(answer, dict) else None
    return value if isinstance(value, dict) else {}


def exact_id_set(mapping):
    return set(mapping) == set(TARGET_IDS)


def check_determinations(answer):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    actual = {app_id: mapped.get(app_id, {}).get("determination") for app_id in TARGET_IDS}
    passed = exact_id_set(mapped) and actual == EXPECTED_DETERMINATIONS
    return passed, f"determinations={actual}, ids={sorted(mapped)}"


def check_code_family(answer, code_family, action_family, family_name):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    if not exact_id_set(mapped):
        return False, f"application id set mismatch: {sorted(mapped)}"
    actual_codes = {}
    actual_actions = {}
    expected_codes = {}
    expected_actions = {}
    for app_id in TARGET_IDS:
        item = mapped.get(app_id, {})
        raw_codes = as_set(item.get("deficiency_codes"))
        raw_actions = as_set(item.get("required_actions"))
        if raw_codes is None or raw_actions is None:
            return False, f"{app_id} deficiency_codes or required_actions is not a list"
        actual_codes[app_id] = raw_codes & code_family
        actual_actions[app_id] = raw_actions & action_family
        expected_codes[app_id] = EXPECTED_DEFICIENCIES[app_id] & code_family
        expected_actions[app_id] = EXPECTED_ACTIONS[app_id] & action_family
    passed = actual_codes == expected_codes and actual_actions == expected_actions
    return passed, f"{family_name}_codes={actual_codes}, {family_name}_actions={actual_actions}"


def check_financial(answer):
    return check_code_family(answer, FINANCIAL_CODES, FINANCIAL_ACTIONS, "financial")


def check_qualification(answer):
    return check_code_family(answer, QUALIFICATION_CODES, QUALIFICATION_ACTIONS, "qualification")


def check_enforcement(answer):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    if not exact_id_set(mapped):
        return False, f"application id set mismatch: {sorted(mapped)}"
    actual_codes = {}
    actual_actions = {}
    expected_codes = {}
    expected_actions = {}
    actual_deny = {}
    for app_id in TARGET_IDS:
        item = mapped.get(app_id, {})
        raw_codes = as_set(item.get("deficiency_codes"))
        raw_actions = as_set(item.get("required_actions"))
        if raw_codes is None or raw_actions is None:
            return False, f"{app_id} deficiency_codes or required_actions is not a list"
        actual_codes[app_id] = raw_codes & ENFORCEMENT_CODES
        actual_actions[app_id] = raw_actions & ENFORCEMENT_ACTIONS
        expected_codes[app_id] = EXPECTED_DEFICIENCIES[app_id] & ENFORCEMENT_CODES
        expected_actions[app_id] = EXPECTED_ACTIONS[app_id] & ENFORCEMENT_ACTIONS
        actual_deny[app_id] = item.get("determination")
    blocking_determinations = {app_id: actual_deny.get(app_id) for app_id in ["C-TR4-003", "C-TR4-007"]}
    passed = (
        actual_codes == expected_codes
        and actual_actions == expected_actions
        and blocking_determinations == {"C-TR4-003": "DENY", "C-TR4-007": "DENY"}
    )
    return (
        passed,
        f"enforcement_codes={actual_codes}, enforcement_actions={actual_actions}, blocking_determinations={blocking_determinations}",
    )


def check_risk(answer):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    actual_risks = {app_id: mapped.get(app_id, {}).get("risk_tier") for app_id in TARGET_IDS}
    actual_high = set(summary(answer).get("high_risk_application_ids", []))
    passed = exact_id_set(mapped) and actual_risks == EXPECTED_RISK_TIERS and actual_high == EXPECTED_HIGH_RISK
    return passed, f"risk_tiers={actual_risks}, high_risk_application_ids={sorted(actual_high)}"


def check_policy_impact(answer):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    actual_flags = {app_id: mapped.get(app_id, {}).get("policy_impacted") for app_id in TARGET_IDS}
    actual_ids = set(summary(answer).get("policy_impacted_application_ids", []))
    passed = exact_id_set(mapped) and actual_flags == EXPECTED_POLICY_IMPACTED and actual_ids == EXPECTED_POLICY_IDS
    return passed, f"policy_flags={actual_flags}, policy_impacted_application_ids={sorted(actual_ids)}"


def check_counts(answer):
    actual = {key: summary(answer).get(key) for key in EXPECTED_COUNTS}
    passed = actual == EXPECTED_COUNTS
    return passed, f"summary_counts={actual}"


def check_correspondence(answer):
    actual = set(summary(answer).get("stale_or_unverified_correspondence_ids", []))
    passed = actual == EXPECTED_CORRESPONDENCE
    return passed, f"stale_or_unverified_correspondence_ids={sorted(actual)}"


POINTS = [
    (
        "SP001",
        "Correct complete APPROVE/HOLD/DENY determination set for the seven target applications.",
        3,
        check_determinations,
    ),
    (
        "SP002",
        "Correct financial security deficiencies and corrective actions for bond and insurance issues.",
        3,
        check_financial,
    ),
    (
        "SP003",
        "Correct specialty endorsement and experience deficiencies and corrective actions.",
        3,
        check_qualification,
    ),
    (
        "SP004",
        "Correct treatment of blocking unresolved serious complaint and active suspension conflicts.",
        3,
        check_enforcement,
    ),
    (
        "SP005",
        "Correct risk tier classifications and high-risk application summary.",
        2,
        check_risk,
    ),
    (
        "SP006",
        "Correct current-policy impact flags and policy-impacted application summary.",
        2,
        check_policy_impact,
    ),
    (
        "SP007",
        "Correct approve, hold, and deny summary counts.",
        1,
        check_counts,
    ),
    (
        "SP008",
        "Correct stale or unverified correspondence id set.",
        1,
        check_correspondence,
    ),
]


def build_result(answer, load_error=None):
    total_weight = sum(weight for _, _, weight, _ in POINTS)
    rendered = []
    total = 0.0
    for point_id, goal, weight, check in POINTS:
        assigned = weight / total_weight
        if load_error is None:
            passed, details = check(answer)
        else:
            passed, details = False, load_error
        earned = assigned if passed else 0.0
        total += earned
        rendered.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": round(assigned, 10),
                "passed": bool(passed),
                "earned_score": round(earned, 10),
                "details": details,
            }
        )
    return {"score": round(total, 10), "points": rendered}


def main():
    candidate_path = (
        sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    answer, load_error = load_candidate(candidate_path)
    result = build_result(answer, load_error)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
