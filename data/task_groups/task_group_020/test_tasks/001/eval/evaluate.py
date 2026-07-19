#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED_ISSUES = {
    "financing_condition",
    "reverse_break_fee_hhw",
    "escrow",
    "indemnity_cap_basket",
    "milestone_non_compete",
    "employee_tsa",
    "tax_law",
}

EXPECTED_PRIORITY = [
    "financing_condition",
    "reverse_break_fee_hhw",
    "escrow",
    "indemnity_cap_basket",
    "employee_tsa",
    "milestone_non_compete",
    "tax_law",
]

POINTS = [
    ("issue_set", 2, "Correct current issue set and excludes distractors."),
    ("financing_rbf_hhw", 3, "Correct financing, reverse break fee, and HHW/regulatory treatment."),
    ("escrow_math", 2, "Correct escrow percentages, dollars, release period, and action."),
    ("indemnity_basket", 2, "Correct indemnity cap and basket treatment."),
    ("milestone_non_compete", 1, "Correct milestone protection and non-compete posture."),
    ("employee_tsa", 2, "Correct employee transfer, PTO, service credit, and TSA treatment."),
    ("tax_law", 1, "Correct tax allocation and law/forum fixes."),
    ("priority_summary", 2, "Correct priority order and summary metrics."),
]


def load_answer(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "answer" in data and isinstance(data["answer"], dict):
        return data["answer"]
    return data


def norm_str(value):
    return "" if value is None else str(value).strip()


def norm_lower(value):
    return norm_str(value).lower()


def norm_upper(value):
    return norm_str(value).upper()


def as_number(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def num_eq(actual, expected):
    value = as_number(actual)
    if value is None:
        return False
    return math.isclose(value, float(expected), rel_tol=0, abs_tol=0.0001)


def norm_code(value):
    return "".join(ch for ch in norm_lower(value) if ch.isalnum())


def one_of(actual, expected_values):
    actual_norm = norm_lower(actual)
    return actual_norm in {norm_lower(value) for value in expected_values}


POSITION_ALIASES = {
    "no_buyer_financing_condition": [
        "no_buyer_financing_condition",
        "no_financing_condition",
        "PB_SELLER_A:financing_condition:no_buyer_financing_condition",
    ],
    "increase_rbf_and_add_regulatory_efforts_without_hhw": [
        "increase_rbf_and_add_regulatory_efforts_without_hhw",
        "rbf_min_6pct_ev_with_regulatory_efforts_no_hhw",
        "rbf_min_6pct_with_regulatory_efforts",
        "min_6pct_rbf_regulatory_efforts_no_hhw",
        "rbf_min_6pct_ev_with_regulatory_efforts_covenant",
        "pb_seller_a_rbf_min_6pct_no_hhw",
        "rbf_6_percent_regulatory_efforts_no_hhw",
        "rbf_min_6_percent_ev_no_hhw",
        "rbf_min_6_percent_ev_if_financing_condition_remains",
        "rbf_min_6pct_ev_no_hhw",
        "rbf_6_percent_ev_no_hhw",
        "reverse_break_fee_at_least_6_percent_ev_no_hhw",
        "rbf_min_6pct_ev_if_financing_risk_remains",
        "RBF_AT_LEAST_6PCT_EV_NO_HHW",
        "RBF_AT_LEAST_6_PERCENT_EV_NO_HHW",
        "PB_SELLER_A:financing_condition:reverse_break_fee_min_6_0_percent",
    ],
    "reduce_escrow_to_fallback_and_shorten_release": [
        "reduce_escrow_to_fallback_and_shorten_release",
        "escrow_max_10pct_12_month_release",
        "escrow_max_10pct_12_months",
        "max_10pct_escrow_12_month_release",
        "pb_seller_a_escrow_max_10pct_12mo",
        "escrow_max_10_percent_12_month_release",
        "escrow_10_percent_12_month_release",
    ],
    "cap_at_verified_risk_fallback_and_add_standard_basket": [
        "cap_at_verified_risk_fallback_and_add_standard_basket",
        "general_cap_max_12_5pct_with_deductible_basket",
        "indemnity_cap_max_12_5pct_with_basket",
        "max_12_5pct_cap_with_basket",
        "general_cap_max_12_5pct_with_basket",
        "pb_seller_a_indemnity_cap_max_12_5pct_with_basket",
        "cap_max_12_5_percent_with_basket",
        "general_cap_max_12_5_percent_with_basket",
        "cap_12_5_percent_with_basket",
    ],
    "protect_milestone_and_limit_restrictive_covenant": [
        "protect_milestone_and_limit_restrictive_covenant",
        "milestone_covenant_and_retained_business_non_compete_carveout",
        "milestone_protection_narrow_non_compete",
        "add_milestone_covenant_and_non_compete",
        "milestone_covennants_and_narrow_non_compete",
        "milestone_covenants_and_narrow_non_compete",
        "seller_milestone_covenant_narrow_non_compete",
        "milestone_protection_limited_non_compete",
        "milestone_protection_and_limited_non_compete",
    ],
    "define_employee_transfer_pto_service_credit_and_tsa": [
        "define_employee_transfer_pto_service_credit_and_tsa",
        "employee_transfer_service_credit_pto_tsa_6_months",
        "employee_transfer_service_credit_pto_tsa",
        "add_employee_transfer_pto_service_credit_tsa",
        "employee_transfer_pto_service_credit_and_tsa",
        "pb_seller_a_employee_tsa_service_credit_pto",
        "service_credit_pto_transfer_process",
        "employee_transfer_service_credit_and_pto_allocation",
        "employee_service_credit_pto_transfer",
        "transfer_process_service_credit_pto_allocation",
    ],
    "add_tax_allocation_transfer_tax_and_forum_fixes": [
        "add_tax_allocation_transfer_tax_and_forum_fixes",
        "section_1060_transfer_tax_and_law_forum_fixes",
        "section_1060_transfer_tax_law_forum_fix",
        "add_1060_transfer_tax_law_forum_fixes",
        "seller_section_1060_transfer_tax_law_forum_fixes",
        "section_1060_transfer_tax_governing_law",
        "section_1060_allocation_transfer_tax_and_forum_fix",
        "section_1060_transfer_tax_law_forum",
        "section_1060_equal_transfer_tax_delaware_forum",
    ],
}


def position_code_ok(actual, expected):
    allowed = POSITION_ALIASES.get(expected, [expected])
    return norm_code(actual) in {norm_code(value) for value in allowed}


def non_compete_ok(actual, expected):
    if norm_lower(actual) == expected:
        return True
    actual_norm = norm_lower(actual)
    return (
        (
            "narrow" in actual_norm
            and ("acquired" in actual_norm or "transferred" in actual_norm or "sold" in actual_norm)
            and ("business" in actual_norm or "operations" in actual_norm)
        )
        or (
            ("limit" in actual_norm or "limited" in actual_norm or "narrow" in actual_norm)
            and ("acquired business" in actual_norm or "transferred business" in actual_norm)
        )
        or ("milestone" in actual_norm and "carveout" in actual_norm)
    )


def bool_eq(actual, expected):
    if isinstance(actual, bool):
        return actual is expected
    if isinstance(actual, str):
        lowered = actual.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return expected is True
        if lowered in {"false", "no", "0"}:
            return expected is False
    return False


def issue_map(answer):
    issues = answer.get("issue_register", [])
    if not isinstance(issues, list):
        return {}
    out = {}
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue_id = norm_lower(item.get("issue_id"))
        if issue_id and issue_id not in out:
            out[issue_id] = item
    return out


def source_terms(issue):
    terms = issue.get("source_term_ids", [])
    if not isinstance(terms, list):
        return set()
    return {norm_str(x) for x in terms}


def check_fields(issue, expected):
    failures = []
    for key, exp in expected.items():
        actual = issue.get(key)
        if isinstance(exp, (list, tuple, set)):
            ok = one_of(actual, exp)
        elif key == "required_position_code":
            ok = position_code_ok(actual, exp)
        elif key == "non_compete_position":
            ok = non_compete_ok(actual, exp)
        elif isinstance(exp, bool):
            ok = bool_eq(actual, exp)
        elif isinstance(exp, (int, float)):
            ok = num_eq(actual, exp)
        elif key in {"issue_status", "recommended_action", "transfer_tax_split", "business_outcome"}:
            ok = norm_lower(actual) == exp.lower()
        elif key == "risk_rating":
            ok = norm_upper(actual) == exp.upper()
        else:
            ok = actual == exp
        if not ok:
            failures.append({"field": key, "expected": exp, "actual": actual})
    return failures


def check_issue_set(answer, issues):
    actual = set(issues)
    return EXPECTED_ISSUES.issubset(actual), {
        "expected": sorted(EXPECTED_ISSUES),
        "actual": sorted(actual),
        "missing": sorted(EXPECTED_ISSUES - actual),
        "extra": sorted(actual - EXPECTED_ISSUES),
    }


def check_financing_rbf_hhw(answer, issues):
    failures = []
    fin = issues.get("financing_condition", {})
    rbf = issues.get("reverse_break_fee_hhw", {})
    failures += [
        {"issue": "financing_condition", **f}
        for f in check_fields(
            fin,
            {
                "issue_status": ["out_of_policy", "draft_exceeds_playbook"],
                "risk_rating": "HIGH",
                "recommended_action": "delete",
                "business_outcome": "closing_certainty",
                "required_position_code": "no_buyer_financing_condition",
            },
        )
    ]
    if "TERM_PRJ_KEYSTONE_01" not in source_terms(fin):
        failures.append(
            {
                "issue": "financing_condition",
                "field": "source_term_ids",
                "expected": "TERM_PRJ_KEYSTONE_01",
                "actual": fin.get("source_term_ids"),
            }
        )
    failures += [
        {"issue": "reverse_break_fee_hhw", **f}
        for f in check_fields(
            rbf,
            {
                "issue_status": "draft_below_playbook",
                "risk_rating": "HIGH",
                "recommended_action": ["revise", "escalate"],
                "business_outcome": "closing_certainty",
                "required_position_code": "increase_rbf_and_add_regulatory_efforts_without_hhw",
                "draft_percent": 2.0,
                "fallback_percent": 6.0,
                "recommended_percent": 6.0,
                "draft_amount_dollars": 4960000,
                "fallback_amount_dollars": 14880000,
                "recommended_amount_dollars": 14880000,
                "delta_to_required_dollars": 9920000,
                "hhw_required": False,
            },
        )
    ]
    if "TERM_PRJ_KEYSTONE_02" not in source_terms(rbf):
        failures.append(
            {
                "issue": "reverse_break_fee_hhw",
                "field": "source_term_ids",
                "expected": "TERM_PRJ_KEYSTONE_02",
                "actual": rbf.get("source_term_ids"),
            }
        )
    return not failures, {"failures": failures}


def check_escrow_math(answer, issues):
    esc = issues.get("escrow", {})
    failures = check_fields(
        esc,
        {
            "issue_status": "draft_exceeds_playbook",
            "risk_rating": ["HIGH", "MEDIUM"],
            "recommended_action": ["revise", "escalate"],
            "business_outcome": "economic_exposure",
            "required_position_code": "reduce_escrow_to_fallback_and_shorten_release",
            "draft_percent": 12.0,
            "preferred_percent": 8.0,
            "fallback_percent": 10.0,
            "recommended_percent": 10.0,
            "draft_amount_dollars": 29760000,
            "preferred_amount_dollars": 19840000,
            "fallback_amount_dollars": 24800000,
            "recommended_amount_dollars": 24800000,
            "delta_to_required_dollars": 4960000,
            "current_months": 18,
            "fallback_months": 12,
            "recommended_months": 12,
        },
    )
    if "TERM_PRJ_KEYSTONE_04" not in source_terms(esc):
        failures.append(
            {"field": "source_term_ids", "expected": "TERM_PRJ_KEYSTONE_04", "actual": esc.get("source_term_ids")}
        )
    return not failures, {"failures": failures}


def check_indemnity_basket(answer, issues):
    ind = issues.get("indemnity_cap_basket", {})
    failures = check_fields(
        ind,
        {
            "issue_status": "draft_exceeds_playbook",
            "risk_rating": ["HIGH", "MEDIUM"],
            "recommended_action": ["revise", "escalate"],
            "business_outcome": "indemnity_recourse",
            "required_position_code": "cap_at_verified_risk_fallback_and_add_standard_basket",
            "draft_percent": 16.0,
            "preferred_percent": 10.0,
            "fallback_percent": 12.5,
            "recommended_percent": 12.5,
            "draft_amount_dollars": 39680000,
            "preferred_amount_dollars": 24800000,
            "fallback_amount_dollars": 31000000,
            "recommended_amount_dollars": 31000000,
            "delta_to_required_dollars": 8680000,
            "basket_required": True,
        },
    )
    if "TERM_PRJ_KEYSTONE_03" not in source_terms(ind):
        failures.append(
            {"field": "source_term_ids", "expected": "TERM_PRJ_KEYSTONE_03", "actual": ind.get("source_term_ids")}
        )
    return not failures, {"failures": failures}


def check_milestone_non_compete(answer, issues):
    item = issues.get("milestone_non_compete", {})
    failures = check_fields(
        item,
        {
            "issue_status": "missing_required_term",
            "risk_rating": ["MEDIUM", "HIGH"],
            "recommended_action": "add",
            "business_outcome": "milestone_value",
            "required_position_code": "protect_milestone_and_limit_restrictive_covenant",
            "milestone_amount_dollars": 20000000,
            "milestone_protection_required": True,
            "non_compete_position": "narrow_to_acquired_business_only",
        },
    )
    return not failures, {"failures": failures}


def check_employee_tsa(answer, issues):
    item = issues.get("employee_tsa", {})
    failures = check_fields(
        item,
        {
            "issue_status": "missing_required_term",
            "risk_rating": "HIGH",
            "recommended_action": "add",
            "business_outcome": "employee_continuity",
            "required_position_code": "define_employee_transfer_pto_service_credit_and_tsa",
            "preferred_months": 6,
            "fallback_months": 9,
            "recommended_months": 6,
            "total_affected_employees": 174,
            "pto_liability_dollars": 3520000,
            "service_credit_required": True,
            "transition_exposure_high_dollars": 4464000,
        },
    )
    return not failures, {"failures": failures}


def check_tax_law(answer, issues):
    item = issues.get("tax_law", {})
    failures = check_fields(
        item,
        {
            "issue_status": "missing_required_term",
            "risk_rating": "MEDIUM",
            "recommended_action": "add",
            "business_outcome": "tax_allocation",
            "required_position_code": "add_tax_allocation_transfer_tax_and_forum_fixes",
            "section_1060_allocation_required": True,
            "transfer_tax_split": ["equal_split", "50/50", "50/50 split", "50_50_split", "equal", "split_equally"],
            "law_forum_fix_required": True,
        },
    )
    return not failures, {"failures": failures}


def check_priority_summary(answer, issues):
    failures = []
    priority = answer.get("priority_order")
    normalized_priority = [norm_lower(x) for x in priority] if isinstance(priority, list) else []
    if not EXPECTED_PRIORITY[:2] == normalized_priority[:2] or not set(EXPECTED_PRIORITY).issubset(
        set(normalized_priority)
    ):
        failures.append({"field": "priority_order", "expected": EXPECTED_PRIORITY, "actual": priority})
    metrics = answer.get("summary_metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    expected_metrics = {
        "headline_value_dollars": 248000000,
        "upfront_cash_dollars": 228000000,
        "milestone_value_dollars": 20000000,
        "total_quantified_delta_dollars": 23560000,
        "reverse_break_fee_shortfall_dollars": 9920000,
        "escrow_excess_over_fallback_dollars": 4960000,
        "indemnity_cap_excess_over_fallback_dollars": 8680000,
        "total_pto_liability_dollars": 3520000,
        "closing_required_consent_amount_at_risk_dollars": 14490000,
    }
    for key, expected in expected_metrics.items():
        if not num_eq(metrics.get(key), expected):
            failures.append({"field": f"summary_metrics.{key}", "expected": expected, "actual": metrics.get(key)})
    return not failures, {"failures": failures}


CHECKS = {
    "issue_set": check_issue_set,
    "financing_rbf_hhw": check_financing_rbf_hhw,
    "escrow_math": check_escrow_math,
    "indemnity_basket": check_indemnity_basket,
    "milestone_non_compete": check_milestone_non_compete,
    "employee_tsa": check_employee_tsa,
    "tax_law": check_tax_law,
    "priority_summary": check_priority_summary,
}


def evaluate(path):
    try:
        answer = load_answer(path)
    except Exception as exc:
        total_weight = sum(weight for _, weight, _ in POINTS)
        return {
            "score": 0.0,
            "max_score": 1.0,
            "raw_score": 0,
            "raw_max_score": total_weight,
            "points": [
                {
                    "id": point_id,
                    "goal": goal,
                    "weight": weight,
                    "assigned_score": weight / total_weight,
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": f"Could not parse answer JSON: {exc}"},
                }
                for point_id, weight, goal in POINTS
            ],
        }

    issues = issue_map(answer)
    total_weight = sum(weight for _, weight, _ in POINTS)
    raw_score = 0
    point_results = []
    for point_id, weight, goal in POINTS:
        passed, details = CHECKS[point_id](answer, issues)
        if passed:
            raw_score += weight
        assigned = weight / total_weight
        point_results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned,
                "passed": bool(passed),
                "earned_score": assigned if passed else 0.0,
                "details": details,
            }
        )

    return {
        "score": raw_score / total_weight,
        "max_score": 1.0,
        "raw_score": raw_score,
        "raw_max_score": total_weight,
        "points": point_results,
    }


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    result = evaluate(path)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
