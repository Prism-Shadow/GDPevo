#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


POINTS = [
    ("issue_set", 3, "Correct issue set for seller APA review."),
    ("financing_rbf_hhw", 3, "Correct financing condition, reverse break fee, HSR, and HHW treatment."),
    ("escrow", 2, "Correct escrow amount, release, and investment-control calculations."),
    ("indemnity_basket_survival", 2, "Correct indemnity cap, basket, and survival treatment."),
    ("restrictive_covenants", 1, "Correct non-compete and non-solicit treatment."),
    ("employee_tsa", 2, "Correct employee continuity and TSA treatment."),
    ("tax_law", 1, "Correct tax allocation and law/forum treatment."),
    ("priority_summary", 2, "Correct priority order and summary metrics."),
]

EXPECTED_ISSUES = {
    "FINANCING_CONDITION",
    "REVERSE_BREAK_FEE",
    "ESCROW",
    "INDEMNITY_CAP",
    "SURVIVAL_PERIOD",
    "INDEMNITY_BASKET",
    "NON_COMPETE_NON_SOLICIT",
    "EMPLOYEE_CONTINUITY",
    "TRANSITION_SERVICES",
    "TAX_ALLOCATION",
    "GOVERNING_LAW_FORUM",
}

EXPECTED_PRIORITY = [
    "FINANCING_CONDITION",
    "REVERSE_BREAK_FEE",
    "ESCROW",
    "INDEMNITY_CAP",
    "EMPLOYEE_CONTINUITY",
    "TRANSITION_SERVICES",
    "NON_COMPETE_NON_SOLICIT",
    "SURVIVAL_PERIOD",
    "INDEMNITY_BASKET",
    "TAX_ALLOCATION",
    "GOVERNING_LAW_FORUM",
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def norm_id(value):
    return str(value or "").strip().upper()


def norm_enum(value):
    return str(value or "").strip().lower()


def as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.strip().lower() in {"true", "yes", "y"}:
            return True
        if value.strip().lower() in {"false", "no", "n"}:
            return False
    return value


def num_eq(actual, expected):
    if actual is None:
        return False
    try:
        return math.isclose(float(actual), float(expected), abs_tol=0.004)
    except (TypeError, ValueError):
        return False


def int_eq(actual, expected):
    try:
        return int(actual) == int(expected)
    except (TypeError, ValueError):
        return False


def issue_map(answer):
    issues = answer.get("issue_register", [])
    if not isinstance(issues, list):
        return {}
    mapped = {}
    for item in issues:
        if isinstance(item, dict):
            issue_id = norm_id(item.get("issue_id"))
            if issue_id:
                mapped[issue_id] = item
    return mapped


def source_terms(issue):
    values = issue.get("source_term_ids", [])
    if not isinstance(values, list):
        return set()
    return {str(v).strip() for v in values}


def covenant(issue):
    value = issue.get("covenant_limits")
    return value if isinstance(value, dict) else {}


def check_issue_set(answer, issues):
    actual = set(issues)
    return actual == EXPECTED_ISSUES, {
        "expected": sorted(EXPECTED_ISSUES),
        "actual": sorted(actual),
        "missing": sorted(EXPECTED_ISSUES - actual),
        "extra": sorted(actual - EXPECTED_ISSUES),
    }


def check_financing_rbf_hhw(answer, issues):
    fin = issues.get("FINANCING_CONDITION", {})
    rbf = issues.get("REVERSE_BREAK_FEE", {})
    passed = (
        source_terms(fin) == {"TERM_PRJ_JUNIPER_01"}
        and norm_enum(fin.get("issue_status")) == "draft_exceeds_playbook"
        and norm_enum(fin.get("recommended_action")) == "delete"
        and norm_enum(fin.get("risk_rating")) == "high"
        and as_bool(fin.get("hsr_required")) is True
        and as_bool(fin.get("hell_or_high_water_required")) is False
        and norm_enum(fin.get("regulatory_effort_code")) == "reasonable_best_efforts_with_remedy_cap"
        and source_terms(rbf) == {"TERM_PRJ_JUNIPER_02"}
        and norm_enum(rbf.get("issue_status")) == "draft_below_playbook"
        and norm_enum(rbf.get("recommended_action")) == "add"
        and norm_enum(rbf.get("risk_rating")) == "high"
        and num_eq(rbf.get("draft_percent"), 0.0)
        and num_eq(rbf.get("required_fee_percent"), 6.0)
        and int_eq(rbf.get("required_fee_dollars"), 17160000)
        and int_eq(rbf.get("shortfall_dollars"), 17160000)
    )
    return passed, {
        "financing_condition": {
            "source_term_ids": sorted(source_terms(fin)),
            "issue_status": fin.get("issue_status"),
            "recommended_action": fin.get("recommended_action"),
            "risk_rating": fin.get("risk_rating"),
            "hsr_required": fin.get("hsr_required"),
            "hell_or_high_water_required": fin.get("hell_or_high_water_required"),
            "regulatory_effort_code": fin.get("regulatory_effort_code"),
        },
        "reverse_break_fee": {
            "source_term_ids": sorted(source_terms(rbf)),
            "issue_status": rbf.get("issue_status"),
            "recommended_action": rbf.get("recommended_action"),
            "risk_rating": rbf.get("risk_rating"),
            "draft_percent": rbf.get("draft_percent"),
            "required_fee_percent": rbf.get("required_fee_percent"),
            "required_fee_dollars": rbf.get("required_fee_dollars"),
            "shortfall_dollars": rbf.get("shortfall_dollars"),
        },
    }


def check_escrow(answer, issues):
    esc = issues.get("ESCROW", {})
    cov = covenant(esc)
    passed = (
        source_terms(esc) == {"TERM_PRJ_JUNIPER_05"}
        and norm_enum(esc.get("issue_status")) == "draft_exceeds_playbook"
        and norm_enum(esc.get("recommended_action")) == "revise"
        and norm_enum(esc.get("risk_rating")) == "high"
        and num_eq(esc.get("draft_percent"), 14.0)
        and num_eq(esc.get("playbook_preferred_percent"), 8.0)
        and num_eq(esc.get("playbook_fallback_percent"), 10.0)
        and int_eq(esc.get("draft_amount_dollars"), 40040000)
        and int_eq(esc.get("preferred_amount_dollars"), 22880000)
        and int_eq(esc.get("fallback_amount_dollars"), 28600000)
        and int_eq(esc.get("delta_to_fallback_dollars"), 11440000)
        and int_eq(esc.get("draft_months"), 18)
        and int_eq(esc.get("fallback_months"), 12)
        and int_eq(esc.get("delta_to_fallback_months"), 6)
        and norm_enum(cov.get("investment_control")) == "joint_direction_only"
    )
    return passed, {
        "source_term_ids": sorted(source_terms(esc)),
        "draft_percent": esc.get("draft_percent"),
        "playbook_preferred_percent": esc.get("playbook_preferred_percent"),
        "playbook_fallback_percent": esc.get("playbook_fallback_percent"),
        "draft_amount_dollars": esc.get("draft_amount_dollars"),
        "preferred_amount_dollars": esc.get("preferred_amount_dollars"),
        "fallback_amount_dollars": esc.get("fallback_amount_dollars"),
        "delta_to_fallback_dollars": esc.get("delta_to_fallback_dollars"),
        "draft_months": esc.get("draft_months"),
        "fallback_months": esc.get("fallback_months"),
        "delta_to_fallback_months": esc.get("delta_to_fallback_months"),
        "investment_control": cov.get("investment_control"),
    }


def check_indemnity_basket_survival(answer, issues):
    cap = issues.get("INDEMNITY_CAP", {})
    basket = issues.get("INDEMNITY_BASKET", {})
    surv = issues.get("SURVIVAL_PERIOD", {})
    basket_cov = covenant(basket)
    passed = (
        source_terms(cap) == {"TERM_PRJ_JUNIPER_03"}
        and norm_enum(cap.get("issue_status")) == "draft_exceeds_playbook"
        and norm_enum(cap.get("recommended_action")) == "revise"
        and num_eq(cap.get("draft_percent"), 18.0)
        and num_eq(cap.get("playbook_preferred_percent"), 10.0)
        and num_eq(cap.get("playbook_fallback_percent"), 12.5)
        and int_eq(cap.get("draft_amount_dollars"), 51480000)
        and int_eq(cap.get("preferred_amount_dollars"), 28600000)
        and int_eq(cap.get("fallback_amount_dollars"), 35750000)
        and int_eq(cap.get("delta_to_fallback_dollars"), 15730000)
        and norm_enum(basket.get("issue_status")) == "missing_required_term"
        and norm_enum(basket.get("recommended_action")) == "add"
        and norm_enum(basket_cov.get("basket_type")) == "deductible"
        and source_terms(surv) == {"TERM_PRJ_JUNIPER_04"}
        and norm_enum(surv.get("issue_status")) == "draft_exceeds_playbook"
        and norm_enum(surv.get("recommended_action")) == "revise"
        and int_eq(surv.get("draft_months"), 24)
        and int_eq(surv.get("preferred_months"), 12)
        and int_eq(surv.get("fallback_months"), 15)
        and int_eq(surv.get("delta_to_fallback_months"), 9)
    )
    return passed, {
        "indemnity_cap": {
            "source_term_ids": sorted(source_terms(cap)),
            "draft_percent": cap.get("draft_percent"),
            "playbook_preferred_percent": cap.get("playbook_preferred_percent"),
            "playbook_fallback_percent": cap.get("playbook_fallback_percent"),
            "draft_amount_dollars": cap.get("draft_amount_dollars"),
            "preferred_amount_dollars": cap.get("preferred_amount_dollars"),
            "fallback_amount_dollars": cap.get("fallback_amount_dollars"),
            "delta_to_fallback_dollars": cap.get("delta_to_fallback_dollars"),
        },
        "indemnity_basket": {
            "issue_status": basket.get("issue_status"),
            "recommended_action": basket.get("recommended_action"),
            "basket_type": basket_cov.get("basket_type"),
        },
        "survival_period": {
            "source_term_ids": sorted(source_terms(surv)),
            "draft_months": surv.get("draft_months"),
            "preferred_months": surv.get("preferred_months"),
            "fallback_months": surv.get("fallback_months"),
            "delta_to_fallback_months": surv.get("delta_to_fallback_months"),
        },
    }


def check_restrictive_covenants(answer, issues):
    rc = issues.get("NON_COMPETE_NON_SOLICIT", {})
    cov = covenant(rc)
    exclusions = cov.get("employee_non_solicit_exclusions", [])
    if not isinstance(exclusions, list):
        exclusions = []
    exclusions = {norm_enum(item) for item in exclusions}
    passed = (
        norm_enum(rc.get("issue_status")) == "missing_required_term"
        and norm_enum(rc.get("recommended_action")) == "add"
        and norm_enum(rc.get("risk_rating")) == "high"
        and int_eq(cov.get("non_compete_months_max"), 24)
        and int_eq(cov.get("non_solicit_months_max"), 12)
        and norm_enum(cov.get("scope")) == "acquired_business_only"
        and {"general_solicitation", "former_employees"}.issubset(exclusions)
    )
    return passed, {
        "issue_status": rc.get("issue_status"),
        "recommended_action": rc.get("recommended_action"),
        "risk_rating": rc.get("risk_rating"),
        "covenant_limits": cov,
    }


def check_employee_tsa(answer, issues):
    emp = issues.get("EMPLOYEE_CONTINUITY", {})
    tsa = issues.get("TRANSITION_SERVICES", {})
    tsa_cov = covenant(tsa)
    passed = (
        norm_enum(emp.get("issue_status")) == "draft_exceeds_playbook"
        and norm_enum(emp.get("recommended_action")) == "revise"
        and norm_enum(emp.get("risk_rating")) == "high"
        and int_eq(emp.get("employee_count"), 174)
        and int_eq(emp.get("pto_liability_dollars"), 3520000)
        and as_bool(emp.get("service_credit_required")) is True
        and as_bool(emp.get("field_selection_allowed")) is False
        and norm_enum(tsa.get("issue_status")) == "missing_required_term"
        and norm_enum(tsa.get("recommended_action")) == "add"
        and norm_enum(tsa.get("risk_rating")) == "high"
        and int_eq(tsa.get("preferred_months"), 6)
        and int_eq(tsa.get("fallback_months"), 9)
        and as_bool(tsa_cov.get("fees_at_least_cost")) is True
        and as_bool(tsa_cov.get("clean_termination_rights_required")) is True
    )
    return passed, {
        "employee_continuity": {
            "issue_status": emp.get("issue_status"),
            "recommended_action": emp.get("recommended_action"),
            "risk_rating": emp.get("risk_rating"),
            "employee_count": emp.get("employee_count"),
            "pto_liability_dollars": emp.get("pto_liability_dollars"),
            "service_credit_required": emp.get("service_credit_required"),
            "field_selection_allowed": emp.get("field_selection_allowed"),
        },
        "transition_services": {
            "issue_status": tsa.get("issue_status"),
            "recommended_action": tsa.get("recommended_action"),
            "risk_rating": tsa.get("risk_rating"),
            "preferred_months": tsa.get("preferred_months"),
            "fallback_months": tsa.get("fallback_months"),
            "covenant_limits": tsa_cov,
        },
    }


def check_tax_law(answer, issues):
    tax = issues.get("TAX_ALLOCATION", {})
    law = issues.get("GOVERNING_LAW_FORUM", {})
    passed = (
        norm_enum(tax.get("issue_status")) == "missing_required_term"
        and norm_enum(tax.get("recommended_action")) == "add"
        and norm_enum(tax.get("tax_allocation_method")) == "mutual_section_1060"
        and norm_enum(tax.get("transfer_tax_split")) == "50_50"
        and norm_enum(law.get("issue_status")) == "missing_required_term"
        and norm_enum(law.get("recommended_action")) == "add"
        and norm_enum(law.get("governing_law")) == "delaware"
        and norm_enum(law.get("forum")) == "delaware courts"
    )
    return passed, {
        "tax_allocation": {
            "issue_status": tax.get("issue_status"),
            "recommended_action": tax.get("recommended_action"),
            "tax_allocation_method": tax.get("tax_allocation_method"),
            "transfer_tax_split": tax.get("transfer_tax_split"),
        },
        "governing_law_forum": {
            "issue_status": law.get("issue_status"),
            "recommended_action": law.get("recommended_action"),
            "governing_law": law.get("governing_law"),
            "forum": law.get("forum"),
        },
    }


def check_priority_summary(answer, issues):
    priority = [norm_id(item) for item in answer.get("priority_order", [])]
    summary = answer.get("summary_metrics", {})
    if not isinstance(summary, dict):
        summary = {}
    passed = (
        priority == EXPECTED_PRIORITY
        and int_eq(summary.get("issue_count"), 11)
        and int_eq(summary.get("high_risk_count"), 7)
        and int_eq(summary.get("medium_risk_count"), 4)
        and int_eq(summary.get("business_outcome_count"), 7)
        and int_eq(summary.get("headline_value_dollars"), 286000000)
        and int_eq(summary.get("total_quantified_exposure_low_dollars"), 7722000)
        and int_eq(summary.get("total_quantified_exposure_high_dollars"), 26026000)
        and int_eq(summary.get("total_negotiation_delta_dollars"), 44330000)
        and int_eq(summary.get("required_closing_consent_count"), 2)
        and int_eq(summary.get("total_employee_count"), 174)
        and int_eq(summary.get("total_pto_liability_dollars"), 3520000)
    )
    return passed, {
        "priority_order": priority,
        "summary_metrics": summary,
    }


CHECKS = {
    "issue_set": check_issue_set,
    "financing_rbf_hhw": check_financing_rbf_hhw,
    "escrow": check_escrow,
    "indemnity_basket_survival": check_indemnity_basket_survival,
    "restrictive_covenants": check_restrictive_covenants,
    "employee_tsa": check_employee_tsa,
    "tax_law": check_tax_law,
    "priority_summary": check_priority_summary,
}


def evaluate(answer):
    issues = issue_map(answer)
    total_weight = sum(weight for _, weight, _ in POINTS)
    results = []
    score = 0.0
    for point_id, weight, goal in POINTS:
        assigned = weight / total_weight
        passed, details = CHECKS[point_id](answer, issues)
        earned = assigned if passed else 0.0
        score += earned
        results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned,
                "passed": bool(passed),
                "earned_score": earned,
                "details": details,
            }
        )
    return {
        "score": score,
        "max_score": 1.0,
        "points": results,
    }


def main():
    if len(sys.argv) > 2:
        raise SystemExit("Usage: evaluate.py [candidate_answer.json]")
    candidate = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("answer.json")
    try:
        answer = load_json(candidate)
        result = evaluate(answer)
    except Exception as exc:
        total_weight = sum(weight for _, weight, _ in POINTS)
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "error": f"{type(exc).__name__}: {exc}",
            "points": [
                {
                    "id": point_id,
                    "goal": goal,
                    "weight": weight,
                    "assigned_score": weight / total_weight,
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": "Answer could not be evaluated."},
                }
                for point_id, weight, goal in POINTS
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
