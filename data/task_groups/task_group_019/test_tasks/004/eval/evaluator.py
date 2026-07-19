#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
GOLD_PATH = TASK_DIR / "output" / "answer.json"

FINANCIAL_CODES = {
    "bond_shortfall",
    "insurance_expired",
    "insurance_not_current",
    "insurance_shortfall",
    "no_active_bond",
}
FINANCIAL_ACTIONS = {
    "file_active_bond",
    "increase_bond",
    "increase_insurance",
    "provide_current_insurance",
    "renew_insurance",
}
QUALIFICATION_CODES = {"endorsement_not_verified", "experience_shortfall"}
QUALIFICATION_ACTIONS = {"document_experience", "verify_endorsement"}
ENFORCEMENT_CODES = {"active_suspension", "unresolved_serious_complaint"}
ENFORCEMENT_ACTIONS = {"board_review", "clear_suspension", "resolve_complaint"}


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


GOLD = load_json(GOLD_PATH)
TARGET_IDS = [item["application_id"] for item in GOLD["application_decisions"]]
EXPECTED_BY_ID = {item["application_id"]: item for item in GOLD["application_decisions"]}
EXPECTED_COUNTS = {
    "approve_count": GOLD["summary"]["approve_count"],
    "hold_count": GOLD["summary"]["hold_count"],
    "deny_count": GOLD["summary"]["deny_count"],
}
EXPECTED_HIGH_RISK = set(GOLD["summary"]["high_risk_application_ids"])
EXPECTED_POLICY_IDS = set(GOLD["summary"]["policy_impacted_application_ids"])
EXPECTED_CORRESPONDENCE = set(GOLD["summary"]["stale_or_unverified_correspondence_ids"])


def load_candidate(path):
    try:
        return load_json(path), None
    except Exception as exc:
        return None, f"Unable to read valid JSON: {exc}"


def as_set(value):
    if not isinstance(value, list):
        return None
    return {str(item) for item in value}


def ordered_target_ids(answer):
    items = answer.get("application_decisions") if isinstance(answer, dict) else None
    if not isinstance(items, list):
        return []
    return [item.get("application_id") for item in items if isinstance(item, dict)]


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


def check_coverage(answer):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    observed_order = ordered_target_ids(answer)
    passed = observed_order == TARGET_IDS and exact_id_set(mapped)
    return passed, f"observed_order={observed_order}; expected_order={TARGET_IDS}"


def check_determinations(answer):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    actual = {app_id: mapped.get(app_id, {}).get("determination") for app_id in TARGET_IDS}
    expected = {app_id: EXPECTED_BY_ID[app_id]["determination"] for app_id in TARGET_IDS}
    passed = exact_id_set(mapped) and actual == expected
    return passed, f"determinations={actual}"


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
        expected_codes[app_id] = set(EXPECTED_BY_ID[app_id]["deficiency_codes"]) & code_family
        expected_actions[app_id] = set(EXPECTED_BY_ID[app_id]["required_actions"]) & action_family
    passed = actual_codes == expected_codes and actual_actions == expected_actions
    return passed, f"{family_name}_codes={actual_codes}; {family_name}_actions={actual_actions}"


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
    family_passed, family_details = check_code_family(answer, ENFORCEMENT_CODES, ENFORCEMENT_ACTIONS, "enforcement")
    expected_denials = {app_id for app_id, item in EXPECTED_BY_ID.items() if item["determination"] == "DENY"}
    actual_denials = {app_id for app_id in TARGET_IDS if mapped.get(app_id, {}).get("determination") == "DENY"}
    passed = family_passed and actual_denials == expected_denials
    return passed, f"{family_details}; deny_ids={sorted(actual_denials)}"


def check_policy_impact(answer):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    actual_flags = {app_id: mapped.get(app_id, {}).get("policy_impacted") for app_id in TARGET_IDS}
    actual_basis = {app_id: mapped.get(app_id, {}).get("policy_impact_basis") for app_id in TARGET_IDS}
    expected_flags = {app_id: EXPECTED_BY_ID[app_id]["policy_impacted"] for app_id in TARGET_IDS}
    expected_basis = {app_id: EXPECTED_BY_ID[app_id]["policy_impact_basis"] for app_id in TARGET_IDS}
    actual_ids = as_set(summary(answer).get("policy_impacted_application_ids"))
    passed = (
        exact_id_set(mapped)
        and actual_flags == expected_flags
        and actual_basis == expected_basis
        and actual_ids == EXPECTED_POLICY_IDS
    )
    return (
        passed,
        f"policy_flags={actual_flags}; policy_basis={actual_basis}; "
        f"policy_impacted_application_ids={sorted(actual_ids or [])}",
    )


def check_source_precedence(answer):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    if not exact_id_set(mapped):
        return False, f"application id set mismatch: {sorted(mapped)}"
    actual_codes = {}
    expected_codes = {}
    for app_id in TARGET_IDS:
        raw_codes = as_set(mapped.get(app_id, {}).get("source_precedence_codes"))
        if raw_codes is None:
            return False, f"{app_id} source_precedence_codes is not a list"
        actual_codes[app_id] = raw_codes
        expected_codes[app_id] = set(EXPECTED_BY_ID[app_id]["source_precedence_codes"])
    actual_correspondence = as_set(summary(answer).get("stale_or_unverified_correspondence_ids"))
    passed = actual_codes == expected_codes and actual_correspondence == EXPECTED_CORRESPONDENCE
    return (
        passed,
        f"source_precedence_codes={actual_codes}; "
        f"stale_or_unverified_correspondence_ids={sorted(actual_correspondence or [])}",
    )


def check_risk(answer):
    mapped, err = decision_map(answer)
    if err:
        return False, err
    actual_risks = {app_id: mapped.get(app_id, {}).get("risk_tier") for app_id in TARGET_IDS}
    expected_risks = {app_id: EXPECTED_BY_ID[app_id]["risk_tier"] for app_id in TARGET_IDS}
    actual_high = as_set(summary(answer).get("high_risk_application_ids"))
    passed = exact_id_set(mapped) and actual_risks == expected_risks and actual_high == EXPECTED_HIGH_RISK
    return passed, f"risk_tiers={actual_risks}; high_risk_application_ids={sorted(actual_high or [])}"


def check_counts(answer):
    actual = {key: summary(answer).get(key) for key in EXPECTED_COUNTS}
    passed = actual == EXPECTED_COUNTS
    return passed, f"summary_counts={actual}"


POINTS = [
    (
        "SP001",
        "Includes exactly the fifteen target applications in application_id order.",
        1,
        check_coverage,
    ),
    (
        "SP002",
        "Correct complete APPROVE/HOLD/DENY determination set for the target applications.",
        3,
        check_determinations,
    ),
    (
        "SP003",
        "Correct financial-security deficiencies and corrective actions.",
        3,
        check_financial,
    ),
    (
        "SP004",
        "Correct endorsement and experience deficiencies and corrective actions.",
        3,
        check_qualification,
    ),
    (
        "SP005",
        "Correct release-blocker treatment for active suspension and unresolved serious enforcement records.",
        3,
        check_enforcement,
    ),
    (
        "SP006",
        "Correct current-policy impact flags, bases, and summary set.",
        3,
        check_policy_impact,
    ),
    (
        "SP007",
        "Correct source-precedence codes and stale or unverified correspondence rollup.",
        3,
        check_source_precedence,
    ),
    (
        "SP008",
        "Correct risk tier classifications and high-risk application summary.",
        2,
        check_risk,
    ),
    (
        "SP009",
        "Correct approve, hold, and deny summary counts.",
        1,
        check_counts,
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
    candidate_path = sys.argv[1] if len(sys.argv) > 1 else GOLD_PATH
    answer, load_error = load_candidate(candidate_path)
    result = build_result(answer, load_error)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
