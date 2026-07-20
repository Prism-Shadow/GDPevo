#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED_ISSUES = {
    "CUSTOMER_CONSENT_TERMINATION_RIGHT",
    "FIELD_EMPLOYEE_CONTINUITY_PTO",
    "GOVERNING_LAW_FORUM_FIX",
    "IP_DOMAIN_TRANSITION_MISSING",
    "OUTSIDE_DATE_EXTENSION_MISSING",
    "SECTION_1060_ALLOCATION_MISSING",
    "TRANSFER_TAX_SPLIT_MISSING",
    "TSA_SCOPE_DURATION_FEES",
}

EXPECTED_REDLINES = {
    "CUSTOMER_CONSENT_CONDITION",
    "EMPLOYEE_CONTINUITY",
    "GOVERNING_LAW_FORUM",
    "IP_DOMAIN_TRANSITION",
    "OUTSIDE_DATE_EXTENSION",
    "SECTION_1060_ALLOCATION",
    "TRANSFER_TAX_SPLIT",
    "TSA_SCOPE_FEES",
}

EXPECTED_PRIORITY = [
    "TSA_SCOPE_DURATION_FEES",
    "IP_DOMAIN_TRANSITION_MISSING",
    "FIELD_EMPLOYEE_CONTINUITY_PTO",
    "CUSTOMER_CONSENT_TERMINATION_RIGHT",
    "OUTSIDE_DATE_EXTENSION_MISSING",
    "SECTION_1060_ALLOCATION_MISSING",
    "TRANSFER_TAX_SPLIT_MISSING",
    "GOVERNING_LAW_FORUM_FIX",
]


def load_candidate(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def as_dict(items, key):
    if not isinstance(items, list):
        return {}
    out = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get(key), str):
            out[item[key]] = item
    return out


def get_path(obj, *keys):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def set_eq(value, expected):
    return isinstance(value, list) and set(value) == set(expected)


def bool_is(value, expected=True):
    return value is expected


def check_issue_set(data, issues, redlines):
    ok = (
        data.get("deal_id") == "PRJ_ORION"
        and data.get("client_side") == "seller"
        and set(issues) == EXPECTED_ISSUES
        and set(redlines) == EXPECTED_REDLINES
    )
    return ok, {
        "issue_ids": sorted(issues),
        "redline_ids": sorted(redlines),
        "expected_issue_ids": sorted(EXPECTED_ISSUES),
        "expected_redline_ids": sorted(EXPECTED_REDLINES),
    }


def check_ip_domain(issues, redlines):
    issue = issues.get("IP_DOMAIN_TRANSITION_MISSING", {})
    terms = get_path(redlines.get("IP_DOMAIN_TRANSITION", {}), "must_have_terms") or {}
    ok = (
        issue.get("issue_status") == "missing_required_term"
        and issue.get("risk_rating") == "HIGH"
        and issue.get("recommended_action") == "add"
        and get_path(issue, "draft_value_normalized", "transitional_trademark_license_present") is False
        and get_path(issue, "draft_value_normalized", "domain_redirect_present") is False
        and terms.get("transitional_trademark_license_required") is True
        and terms.get("trademark_license_days") == 180
        and terms.get("domain_redirect_required") is True
        and terms.get("domain_redirect_months") == 12
        and terms.get("redirect_type") == "301_OR_302"
        and terms.get("all_pages_and_subdomains") is True
        and terms.get("buyer_maintain_domains") is True
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_tsa(issues, redlines):
    issue = issues.get("TSA_SCOPE_DURATION_FEES", {})
    redline = redlines.get("TSA_SCOPE_FEES", {})
    terms = redline.get("must_have_terms", {}) if isinstance(redline, dict) else {}
    services = terms.get("services")
    ok = (
        issue.get("issue_status") == "draft_exceeds_playbook"
        and issue.get("risk_rating") == "HIGH"
        and issue.get("recommended_action") == "revise"
        and get_path(issue, "draft_value_normalized", "draft_months") == 15
        and get_path(issue, "draft_value_normalized", "fee_model") == "at_cost"
        and get_path(issue, "draft_value_normalized", "stranded_cost_gap_dollars") == 3800000
        and get_path(issue, "required_position_normalized", "preferred_months") == 6
        and get_path(issue, "required_position_normalized", "fallback_months") == 9
        and get_path(issue, "required_position_normalized", "excess_months_over_fallback") == 6
        and redline.get("redline_action") == "revise"
        and terms.get("max_duration_months") == 9
        and terms.get("preferred_duration_months") == 6
        and set_eq(services, ["billing", "dispatch", "HR"])
        and terms.get("fee_model") == "cost_plus_stranded_overhead"
        and terms.get("stranded_cost_reimbursement_dollars") == 3800000
        and terms.get("clean_termination_right") is True
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_tax(redlines):
    section = get_path(redlines.get("SECTION_1060_ALLOCATION", {}), "must_have_terms") or {}
    transfer = get_path(redlines.get("TRANSFER_TAX_SPLIT", {}), "must_have_terms") or {}
    ok = (
        section.get("tax_allocation_method") == "mutually_agreed_section_1060"
        and section.get("mutually_agreed_within_days") == 90
        and section.get("form_8594_consistency") is True
        and transfer.get("seller_percent") == 50
        and transfer.get("buyer_percent") == 50
        and transfer.get("bulk_sale_costs_same_split") is True
    )
    return ok, {"section_1060": section, "transfer_tax": transfer}


def check_employee(issues, redlines):
    issue = issues.get("FIELD_EMPLOYEE_CONTINUITY_PTO", {})
    terms = get_path(redlines.get("EMPLOYEE_CONTINUITY", {}), "must_have_terms") or {}
    ok = (
        issue.get("risk_rating") == "HIGH"
        and issue.get("recommended_action") == "revise"
        and get_path(issue, "draft_value_normalized", "buyer_cherry_pick_right") is True
        and get_path(issue, "draft_value_normalized", "rejects_accrued_pto") is True
        and get_path(issue, "draft_value_normalized", "affected_employee_count") == 124
        and get_path(issue, "quantified_impact_dollars") == 1240000
        and terms.get("affected_employee_group") == "field and operations"
        and terms.get("must_offer_all_field_operations") is True
        and terms.get("affected_employee_count") == 124
        and terms.get("service_credit_required") is True
        and terms.get("accrued_pto_allocation_required") is True
        and terms.get("pto_liability_dollars") == 1240000
        and terms.get("warn_risk") == "medium"
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_deadline(issues, redlines):
    issue = issues.get("OUTSIDE_DATE_EXTENSION_MISSING", {})
    terms = get_path(redlines.get("OUTSIDE_DATE_EXTENSION", {}), "must_have_terms") or {}
    ok = (
        issue.get("issue_status") == "missing_required_term"
        and issue.get("recommended_action") == "add"
        and get_path(issue, "draft_value_normalized", "hsr_required") is True
        and get_path(issue, "required_position_normalized", "initial_outside_date_days") == 120
        and get_path(issue, "required_position_normalized", "seller_regulatory_extension_days") == 30
        and terms.get("initial_outside_date_days") == 120
        and terms.get("seller_regulatory_extension_days") == 30
        and terms.get("applies_because_hsr_required") is True
        and terms.get("maximum_without_board_approval_days") == 240
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_law_forum(issues, redlines):
    issue = issues.get("GOVERNING_LAW_FORUM_FIX", {})
    terms = get_path(redlines.get("GOVERNING_LAW_FORUM", {}), "must_have_terms") or {}
    ok = (
        issue.get("issue_status") == "missing_required_term"
        and issue.get("recommended_action") == "add"
        and terms.get("governing_law") == "Delaware"
        and terms.get("forum") == "Delaware Court of Chancery or Delaware federal court"
        and terms.get("apply_to_ancillary_documents") is True
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_risk_summary(data):
    risk = data.get("operational_risk", {})
    exposures = risk.get("quantified_exposures", {}) if isinstance(risk, dict) else {}
    ok = (
        risk.get("overall_risk_rating") == "HIGH"
        and risk.get("overall_posture") == "revise_before_signing"
        and risk.get("priority_order") == EXPECTED_PRIORITY
        and exposures.get("stranded_cost_gap_dollars") == 3800000
        and exposures.get("field_operations_pto_liability_dollars") == 1240000
        and exposures.get("required_closing_consent_amount_at_risk_dollars") == 11740000
        and exposures.get("top_customer_annual_revenue_at_risk_dollars") == 16830000
        and exposures.get("transition_disruption_high_dollars") == 3563999
        and set_eq(risk.get("required_closing_consent_ids"), ["CNS_PRJ_ORION_01", "CNS_PRJ_ORION_03"])
        and set_eq(risk.get("material_contract_consent_ids"), ["MAT_PRJ_ORION_01", "MAT_PRJ_ORION_03"])
    )
    return ok, {"operational_risk": risk}


SCORING_POINTS = [
    ("issue_set", 2, "Correct transition issue and redline identifier sets for PRJ_ORION.", check_issue_set),
    (
        "trademark_domain_transition",
        2,
        "Correct missing trademark license and domain redirect redline.",
        check_ip_domain,
    ),
    ("tsa_scope_and_fees", 3, "Correct TSA duration, scope, fee, and stranded-cost treatment.", check_tsa),
    ("tax_allocation", 2, "Correct Section 1060 and transfer-tax allocation redlines.", check_tax),
    ("employee_continuity", 2, "Correct field employee continuity and PTO treatment.", check_employee),
    ("outside_date", 1, "Correct outside date and seller regulatory extension protection.", check_deadline),
    ("law_forum", 1, "Correct Delaware law and forum fix.", check_law_forum),
    (
        "risk_summary",
        3,
        "Correct operational risk posture, priority order, and quantified exposure summary.",
        check_risk_summary,
    ),
]


def main():
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    max_score = sum(weight for _, weight, _, _ in SCORING_POINTS)
    try:
        data = load_candidate(candidate_path)
    except Exception as exc:
        points = [
            {
                "id": point_id,
                "weight": weight,
                "assigned_score": weight / max_score,
                "passed": False,
                "earned_score": 0,
                "details": {"error": f"Unable to parse candidate JSON: {exc}"},
            }
            for point_id, weight, _, _ in SCORING_POINTS
        ]
        print(
            json.dumps(
                {"score": 0, "max_score": 1, "raw_score": 0, "raw_max_score": max_score, "points": points}, indent=2
            )
        )
        return

    issues = as_dict(data.get("transition_issues"), "issue_id")
    redlines = as_dict(data.get("required_redlines"), "redline_id")
    points = []
    raw_score = 0
    for point_id, weight, goal, func in SCORING_POINTS:
        if point_id == "issue_set":
            passed, details = func(data, issues, redlines)
        elif point_id in {
            "trademark_domain_transition",
            "tsa_scope_and_fees",
            "employee_continuity",
            "outside_date",
            "law_forum",
        }:
            passed, details = func(issues, redlines)
        elif point_id == "tax_allocation":
            passed, details = func(redlines)
        else:
            passed, details = func(data)
        if passed:
            raw_score += weight
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": weight / max_score,
                "passed": bool(passed),
                "earned_score": (weight / max_score) if passed else 0,
                "details": details,
            }
        )

    print(
        json.dumps(
            {
                "score": raw_score / max_score,
                "max_score": 1,
                "raw_score": raw_score,
                "raw_max_score": max_score,
                "points": points,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
