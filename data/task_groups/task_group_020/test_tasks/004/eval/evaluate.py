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
    "CUSTOMER_CONSENT_TERMINATION_RIGHT",
    "OUTSIDE_DATE_EXTENSION_MISSING",
    "IP_DOMAIN_TRANSITION_MISSING",
    "FIELD_EMPLOYEE_CONTINUITY_PTO",
    "SECTION_1060_ALLOCATION_MISSING",
    "TRANSFER_TAX_SPLIT_MISSING",
    "GOVERNING_LAW_FORUM_FIX",
]

EXPECTED_REDLINE_LINKS = {
    "CUSTOMER_CONSENT_CONDITION": ("CUSTOMER_CONSENT_TERMINATION_RIGHT", "revise"),
    "EMPLOYEE_CONTINUITY": ("FIELD_EMPLOYEE_CONTINUITY_PTO", "revise"),
    "GOVERNING_LAW_FORUM": ("GOVERNING_LAW_FORUM_FIX", "add"),
    "IP_DOMAIN_TRANSITION": ("IP_DOMAIN_TRANSITION_MISSING", "add"),
    "OUTSIDE_DATE_EXTENSION": ("OUTSIDE_DATE_EXTENSION_MISSING", "add"),
    "SECTION_1060_ALLOCATION": ("SECTION_1060_ALLOCATION_MISSING", "add"),
    "TRANSFER_TAX_SPLIT": ("TRANSFER_TAX_SPLIT_MISSING", "add"),
    "TSA_SCOPE_FEES": ("TSA_SCOPE_DURATION_FEES", "revise"),
}


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


def set_contains(value, expected):
    return isinstance(value, list) and set(expected).issubset(set(value))


def norm_text(value):
    return "" if value is None else str(value).strip().lower()


def get_any(obj, *keys):
    if not isinstance(obj, dict):
        return None
    for key in keys:
        if key in obj:
            return obj[key]
    return None


def boolish(value, expected=True):
    if isinstance(value, bool):
        return value is expected
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value) is expected
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "required", "present", "included"}:
            return expected is True
        if lowered in {
            "false",
            "no",
            "silent",
            "missing",
            "not_applicable",
            "none",
            "not addressed",
            "not_found_in_current_records",
        }:
            return expected is False
    return False


def false_or_silent(value):
    return boolish(value, False) or norm_text(value) in {
        "silent",
        "missing",
        "not present",
        "not addressed",
        "not_found_in_current_records",
    }


def action_ok(value, *allowed):
    return norm_text(value) in {norm_text(item) for item in allowed}


def value_in(value, *allowed):
    return norm_text(value) in {norm_text(item) for item in allowed}


def any_key_true(*containers, keys):
    for container in containers:
        if not isinstance(container, dict):
            continue
        for key in keys:
            value = container.get(key)
            if boolish(value, True):
                return True
            if isinstance(value, list) and value:
                return True
    return False


def any_number(expected, *containers, keys):
    for container in containers:
        if not isinstance(container, dict):
            continue
        for key in keys:
            if container.get(key) == expected:
                return True
    return False


def service_set_ok(value):
    if not isinstance(value, list):
        return False
    normalized = {norm_text(item).replace("_", " ").replace("-", " ") for item in value}
    joined = " ".join(normalized)
    return {"identity", "billing"}.issubset(normalized) and (
        "tier two support" in normalized or "support" in normalized or ("tier" in joined and "support" in joined)
    )


def check_issue_set(data, issues, redlines):
    ok = (
        data.get("deal_id") == "PRJ_NIMBUS"
        and data.get("client_side") == "seller"
        and EXPECTED_ISSUES.issubset(set(issues))
    )
    return ok, {
        "issue_ids": sorted(issues),
        "expected_issue_ids": sorted(EXPECTED_ISSUES),
    }


def check_ip_domain(issues, redlines):
    issue = issues.get("IP_DOMAIN_TRANSITION_MISSING", {})
    terms = get_path(redlines.get("IP_DOMAIN_TRANSITION", {}), "must_have_terms") or {}
    draft = issue.get("draft_value_normalized", {}) if isinstance(issue, dict) else {}
    required = issue.get("required_position_normalized", {}) if isinstance(issue, dict) else {}
    ok = (
        issue.get("issue_status") == "missing_required_term"
        and value_in(issue.get("risk_rating"), "HIGH", "MEDIUM")
        and issue.get("recommended_action") == "add"
        and (
            false_or_silent(
                get_any(
                    draft,
                    "transitional_trademark_license_present",
                    "ip_transition_terms",
                    "ip_transition_license",
                    "ip_transition_provision_present",
                    "ip_transition_rights_present",
                    "current_draft_term",
                )
            )
            or any_key_true(
                required,
                terms,
                keys=[
                    "domain_transition_required",
                    "trademark_phaseout_required",
                    "domain_transition_plan_required",
                    "assign_or_license_required_ip_for_transferred_business",
                    "shared_system_separation_required",
                    "seller_system_separation_milestones_required",
                    "domain_transfer_schedule_required",
                    "domain_and_dns_inventory_required",
                    "domain_and_ip_assignment_schedule_required",
                    "scheduled_ip_and_domains_required",
                    "domain_transfer_and_redirect_required",
                    "ip_domain_transition_required",
                    "transition_license_required",
                    "ip_transition_license_required",
                    "transition_ip_license_required",
                    "ip_transition_required",
                    "ip_domain_transition_plan_required",
                    "temporary_ip_license_required",
                ],
            )
        )
        and (
            false_or_silent(
                get_any(
                    draft,
                    "domain_redirect_present",
                    "domain_redirect_terms",
                    "domain_redirect_provision_present",
                    "domain_redirects_present",
                )
            )
            or any_key_true(
                required,
                terms,
                keys=[
                    "domain_redirect_required",
                    "domain_redirects_required",
                    "domain_transition_required",
                    "domain_transfer_and_redirect_required",
                    "domain_transfer_schedule_required",
                    "domain_transition_plan_required",
                    "domain_and_dns_inventory_required",
                    "domain_and_ip_assignment_schedule_required",
                    "scheduled_ip_and_domains_required",
                ],
            )
        )
        and any_key_true(
            required,
            terms,
            keys=[
                "assign_or_license_required_ip_for_transferred_business",
                "shared_system_separation_required",
                "seller_system_separation_milestones_required",
                "domain_transition_required",
                "domain_transfer_schedule_required",
                "domain_and_dns_inventory_required",
                "domain_and_ip_assignment_schedule_required",
                "domain_transfer_and_redirect_required",
                "transitional_trademark_license_required",
                "transition_license_required",
                "ip_transition_license_required",
                "transition_license_for_shared_systems",
                "ip_transition_plan_required",
                "transitional_ip_license",
                "transition_ip_license",
                "temporary_ip_license_required",
                "ip_transition_required",
            ],
        )
        and (
            get_any(required, "redirect_type", "domain_redirect_type") in {"301_OR_302", "302_ONLY"}
            or get_any(terms, "redirect_type", "domain_redirect_type") in {"301_OR_302", "302_ONLY"}
        )
        and (
            any_number(
                180,
                required,
                terms,
                keys=["trademark_license_days", "license_days", "transitional_trademark_license_days"],
            )
            or any_number(
                9,
                required,
                terms,
                keys=[
                    "domain_redirect_months",
                    "maximum_redirect_months",
                    "redirect_duration_months",
                    "fallback_redirect_duration_months",
                ],
            )
            or any_number(
                12,
                required,
                terms,
                keys=[
                    "domain_redirect_months",
                    "maximum_redirect_months",
                    "redirect_duration_months",
                    "fallback_redirect_duration_months",
                ],
            )
            or any_key_true(
                required,
                terms,
                keys=[
                    "buyer_domain_maintenance_required",
                    "buyer_maintain_domains",
                    "seller_retained_ip_and_domains_protected",
                    "seller_system_access_end_state",
                    "shared_system_separation_required",
                    "seller_system_separation_milestones_required",
                    "seller_system_separation_cooperation_required",
                    "seller_control_after_transition",
                    "seller_retains_control_after_transition",
                    "seller_retained_ip_excluded",
                    "seller_owned_marks_and_legacy_domains_excluded_except_transition_use",
                    "redirect_duration_capped_by_tsa",
                    "redirect_duration_months_capped_at_tsa_duration",
                    "transition_period_aligned_to_tsa_fallback_months",
                    "cutover_support_required",
                ],
            )
        )
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_tsa(issues, redlines):
    issue = issues.get("TSA_SCOPE_DURATION_FEES", {})
    terms = get_path(redlines.get("TSA_SCOPE_FEES", {}), "must_have_terms") or {}
    ip_issue = issues.get("IP_DOMAIN_TRANSITION_MISSING", {})
    ip_terms = get_path(redlines.get("IP_DOMAIN_TRANSITION", {}), "must_have_terms") or {}
    draft = issue.get("draft_value_normalized", {}) if isinstance(issue, dict) else {}
    required = issue.get("required_position_normalized", {}) if isinstance(issue, dict) else {}
    ip_draft = ip_issue.get("draft_value_normalized", {}) if isinstance(ip_issue, dict) else {}
    ip_required = ip_issue.get("required_position_normalized", {}) if isinstance(ip_issue, dict) else {}
    service_scope_ok = (
        service_set_ok(
            get_any(
                terms,
                "services",
                "services_and_systems_covered",
                "services_covered",
                "permitted_scope",
                "covered_services",
            )
        )
        or service_set_ok(get_any(required, "services", "service_scope", "covered_services"))
        or service_set_ok(get_any(draft, "services", "services_scope", "scope", "transition_services_scope"))
        or service_set_ok(get_any(ip_draft, "shared_systems", "shared_systems_context", "shared_systems_to_separate"))
        or service_set_ok(
            get_any(ip_required, "shared_systems", "shared_systems_context", "shared_systems_to_separate")
        )
        or service_set_ok(
            get_any(
                ip_terms,
                "shared_systems",
                "shared_systems_context",
                "shared_systems_to_separate",
                "systems_to_separate",
            )
        )
    )
    ok = (
        set_eq(issue.get("source_term_ids"), ["TERM_PRJ_NIMBUS_01", "TERM_PRJ_NIMBUS_02"])
        and issue.get("issue_status") == "draft_exceeds_playbook"
        and issue.get("risk_rating") == "HIGH"
        and action_ok(issue.get("recommended_action"), "revise", "escalate")
        and get_any(draft, "draft_months", "duration_months") == 18
        and service_set_ok(get_any(draft, "services", "services_scope", "scope", "transition_services_scope"))
        and get_any(draft, "fee_model") == "fixed_below_cost"
        and get_any(
            draft,
            "stranded_cost_gap_dollars",
            "unrecovered_stranded_costs_dollars",
            "unrecovered_stranded_cost_dollars",
        )
        == 9400000
        and get_any(required, "preferred_months", "preferred_duration_months", "preferred_max_duration_months") == 6
        and get_any(required, "fallback_months", "fallback_duration_months", "fallback_max_duration_months") == 9
        and any_number(
            9,
            required,
            terms,
            keys=[
                "max_duration_months",
                "maximum_duration_months",
                "maximum_duration_months_fallback",
                "fallback_duration_months",
                "fallback_months",
                "fallback_max_duration_months",
            ],
        )
        and any_number(
            6,
            required,
            terms,
            keys=[
                "preferred_duration_months",
                "maximum_duration_months_preferred",
                "preferred_months",
                "preferred_max_duration_months",
            ],
        )
        and service_scope_ok
        and get_any(terms, "fee_model") == "cost_plus_stranded_overhead"
        and (
            any_number(
                9400000,
                terms,
                keys=[
                    "stranded_cost_reimbursement_dollars",
                    "unrecovered_stranded_costs_to_recover_dollars",
                    "recover_stranded_cost_gap_dollars",
                    "stranded_cost_gap_dollars",
                    "stranded_cost_recovery_dollars",
                    "stranded_cost_gap_to_eliminate_dollars",
                ],
            )
            or any_number(
                0,
                terms,
                keys=[
                    "unrecovered_stranded_costs_allowed_dollars",
                    "stranded_cost_gap_dollars",
                    "stranded_cost_gap_to_eliminate_dollars",
                ],
            )
            or any_key_true(
                required,
                terms,
                keys=[
                    "stranded_cost_recovery_required",
                    "recover_stranded_costs",
                    "fees_must_recover_stranded_costs",
                    "stranded_cost_recovery",
                ],
            )
        )
        and any_key_true(
            required,
            terms,
            keys=[
                "clean_termination_right",
                "clean_termination_rights_required",
                "clean_termination_rights",
                "clean_termination_right_required",
            ],
        )
        and issue.get("quantified_impact_dollars") == 9400000
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_employee(issues, redlines):
    issue = issues.get("FIELD_EMPLOYEE_CONTINUITY_PTO", {})
    terms = get_path(redlines.get("EMPLOYEE_CONTINUITY", {}), "must_have_terms") or {}
    draft = issue.get("draft_value_normalized", {}) if isinstance(issue, dict) else {}
    required = issue.get("required_position_normalized", {}) if isinstance(issue, dict) else {}
    ok = (
        value_in(issue.get("issue_status"), "out_of_policy", "draft_below_playbook", "missing_required_term")
        and value_in(issue.get("risk_rating"), "HIGH", "MEDIUM")
        and value_in(issue.get("recommended_action"), "revise", "add")
        and (
            boolish(
                get_any(
                    draft,
                    "buyer_cherry_pick_right",
                    "buyer_selection_rights",
                    "buyer_selection_right",
                    "buyer_may_select_continuing_employees",
                ),
                True,
            )
            or "select" in norm_text(get_any(draft, "draft_treatment"))
        )
        and (
            get_any(draft, "affected_employee_group", "employee_group") == "field and operations"
            or get_any(
                draft,
                "affected_employee_count",
                "employee_count",
                "count",
                "field_operations_count",
                "field_operations_employee_count",
            )
            == 37
        )
        and get_any(
            draft,
            "affected_employee_count",
            "employee_count",
            "count",
            "field_operations_count",
            "field_operations_employee_count",
        )
        == 37
        and issue.get("quantified_impact_dollars") == 1240000
        and get_any(terms, "affected_employee_group") in {"field and operations", None}
        and any_key_true(
            required,
            terms,
            keys=[
                "must_offer_all_field_operations",
                "define_transfer_process",
                "defined_transfer_process",
                "defined_transfer_process_required",
                "continuing_employee_transfer_process",
                "field_operations_transfer_process",
                "limit_buyer_selection_rights",
                "buyer_selection_limits_required",
                "buyer_selection_rights_limited",
                "no_buyer_cherry_picking",
                "transfer_process_required",
            ],
        )
        and any_key_true(
            required,
            terms,
            keys=[
                "service_credit_required",
                "credit_prior_service",
                "prior_service_credit",
                "prior_service_credit_required",
            ],
        )
        and any_key_true(
            required,
            terms,
            keys=["accrued_pto_allocation_required", "allocate_accrued_pto_liability", "allocate_accrued_pto"],
        )
        and (
            any_number(
                1240000,
                terms,
                keys=[
                    "pto_liability_dollars",
                    "field_operations_pto_liability_dollars",
                    "allocate_accrued_pto_liability_dollars",
                    "accrued_pto_allocation_dollars",
                    "pto_liability_allocation_dollars",
                    "accrued_pto_allocation",
                ],
            )
            or get_any(draft, "pto_liability_dollars", "field_operations_pto_liability_dollars") == 1240000
        )
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_tax(redlines):
    section = get_path(redlines.get("SECTION_1060_ALLOCATION", {}), "must_have_terms") or {}
    transfer = get_path(redlines.get("TRANSFER_TAX_SPLIT", {}), "must_have_terms") or {}
    ok = (
        section.get("tax_allocation_method") == "mutually_agreed_section_1060"
        and (
            boolish(
                get_any(
                    section,
                    "form_8594_consistency",
                    "form_8594_consistency_required",
                    "consistent_tax_reporting_required",
                    "consistent_irs_form_8594_reporting_required",
                    "consistent_tax_reporting",
                    "consistent_form_8594_reporting",
                ),
                True,
            )
            or any_key_true(
                section,
                keys=[
                    "allocation_statement_required",
                    "allocation_schedule",
                    "allocation_schedule_required",
                    "allocation_consistent_with_purchase_price_schedule",
                    "seller_review_required",
                    "no_buyer_sole_discretion",
                    "dispute_process_required",
                    "dispute_resolution_required",
                    "allocation_dispute_process",
                    "allocation_dispute_process_required",
                    "tax_dispute_resolution_process",
                    "tax_return_consistency_required",
                    "post_closing_adjustment_conformity",
                ],
            )
        )
        and (
            (
                get_any(transfer, "seller_percent", "seller_share_percent", "transfer_tax_split_percent_seller") == 50
                and get_any(transfer, "buyer_percent", "buyer_share_percent", "transfer_tax_split_percent_buyer") == 50
            )
            or boolish(
                get_any(
                    transfer,
                    "buyer_and_seller_each_pay_half",
                    "transfer_tax_split_required",
                    "transfer_taxes_split_required",
                    "transfer_taxes_shared_by_buyer_and_seller",
                    "split_transfer_taxes_equally",
                    "transfer_tax_allocation",
                    "filing_and_remittance_cooperation",
                    "filing_cooperation",
                    "mutual_cooperation_on_tax_filings",
                ),
                True,
            )
            or get_any(transfer, "transfer_tax_split", "transfer_tax_allocation") == "50/50"
        )
    )
    return ok, {"section_1060": section, "transfer_tax": transfer}


def check_deadline(issues, redlines):
    issue = issues.get("OUTSIDE_DATE_EXTENSION_MISSING", {})
    terms = get_path(redlines.get("OUTSIDE_DATE_EXTENSION", {}), "must_have_terms") or {}
    ok = (
        issue.get("issue_status") == "missing_required_term"
        and issue.get("risk_rating") == "HIGH"
        and issue.get("recommended_action") == "add"
        and (
            boolish(get_path(issue, "draft_value_normalized", "hsr_required"), True)
            or "hsr" in norm_text(get_path(issue, "draft_value_normalized", "regulatory_approval"))
        )
        and (
            (
                get_path(issue, "required_position_normalized", "initial_outside_date_days") == 120
                and get_path(issue, "required_position_normalized", "seller_regulatory_extension_days") == 30
                and get_path(issue, "required_position_normalized", "maximum_without_board_approval_days") == 240
                and terms.get("initial_outside_date_days") == 120
                and terms.get("seller_regulatory_extension_days") == 30
                and terms.get("maximum_without_board_approval_days") == 240
            )
            or any_key_true(
                issue.get("required_position_normalized", {}),
                terms,
                keys=[
                    "automatic_extension_if_hsr_pending",
                    "automatic_extension_for_hsr_clearance",
                    "automatic_extension_for_hsr_delay",
                    "automatic_extension_for_hsr_and_required_consents",
                    "automatic_extension_until_hsr_clearance",
                    "hsr_outside_date_extension_required",
                    "regulatory_approval_extension_required",
                    "regulatory_extension_required",
                    "seller_regulatory_extension_required",
                    "consent_extension_required",
                    "required_consent_extension_required",
                    "outside_date_extension_required",
                    "outside_date_extension_for_regulatory_delay",
                    "finite_outside_date_extension_required",
                    "applies_because_hsr_required",
                ],
            )
        )
        and issue.get("quantified_impact_dollars") == 27900000
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_law_forum(issues, redlines):
    issue = issues.get("GOVERNING_LAW_FORUM_FIX", {})
    terms = get_path(redlines.get("GOVERNING_LAW_FORUM", {}), "must_have_terms") or {}
    draft = issue.get("draft_value_normalized", {}) if isinstance(issue, dict) else {}
    ok = (
        issue.get("issue_status") == "missing_required_term"
        and value_in(issue.get("risk_rating"), "LOW", "MEDIUM")
        and issue.get("recommended_action") == "add"
        and (
            get_any(draft, "governing_law_specified", "governing_law_present", "present_in_current_draft") is False
            or norm_text(get_any(draft, "governing_law")) == "silent"
        )
        and (
            get_any(draft, "forum_specified", "forum_present", "present_in_current_draft") is False
            or norm_text(get_any(draft, "forum", "exclusive_forum")) in {"silent", "false", "other"}
        )
        and (
            terms.get("governing_law") == "Delaware"
            or get_any(issue.get("required_position_normalized", {}), "governing_law") == "Delaware"
        )
        and terms.get("forum") == "Delaware Court of Chancery or Delaware federal court"
        and (
            boolish(get_any(terms, "apply_to_ancillary_documents", "exclusive_forum", "exclusive_jurisdiction"), True)
        )
    )
    return ok, {"issue": issue, "redline_terms": terms}


def check_operational_risk(data):
    risk = data.get("operational_risk", {})
    exposures = risk.get("quantified_exposures", {}) if isinstance(risk, dict) else {}
    ok = (
        risk.get("overall_risk_rating") == "HIGH"
        and value_in(risk.get("overall_posture"), "revise_before_signing", "escalate_to_business_lead")
        and isinstance(risk.get("priority_order"), list)
        and set(EXPECTED_PRIORITY).issubset(set(risk.get("priority_order")))
        and len(set(risk.get("priority_order")[:4]).intersection(set(EXPECTED_PRIORITY[:4]))) >= 3
        and exposures.get("stranded_cost_gap_dollars") == 9400000
        and exposures.get("field_operations_pto_liability_dollars") == 1240000
        and exposures.get("required_closing_consent_amount_at_risk_dollars") == 34950000
        and exposures.get("top_customer_annual_revenue_at_risk_dollars") == 52700000
        and exposures.get("closing_certainty_high_dollars") == 27900000
        and exposures.get("transition_disruption_high_dollars") == 11160000
        and set_eq(risk.get("required_closing_consent_ids"), ["CNS_PRJ_NIMBUS_01", "CNS_PRJ_NIMBUS_03"])
        and set_eq(risk.get("material_contract_consent_ids"), ["MAT_PRJ_NIMBUS_01", "MAT_PRJ_NIMBUS_03"])
        and isinstance(risk.get("business_outcomes_protected"), list)
        and len(risk.get("business_outcomes_protected")) >= 3
    )
    return ok, {"operational_risk": risk}


def check_redline_package(redlines):
    details = {}
    for redline_id, (expected_issue, expected_action) in EXPECTED_REDLINE_LINKS.items():
        redline = redlines.get(redline_id, {})
        details[redline_id] = {
            "related_issue_id": redline.get("related_issue_id"),
            "redline_action": redline.get("redline_action"),
        }
    ok = EXPECTED_REDLINES.issubset(set(redlines)) and all(
        redlines.get(redline_id, {}).get("related_issue_id") == issue_id
        and action_ok(
            redlines.get(redline_id, {}).get("redline_action"),
            action,
            "escalate" if action == "revise" else action,
            "add" if redline_id == "EMPLOYEE_CONTINUITY" else action,
        )
        and isinstance(redlines.get(redline_id, {}).get("must_have_terms"), dict)
        and bool(redlines.get(redline_id, {}).get("must_have_terms"))
        for redline_id, (issue_id, action) in EXPECTED_REDLINE_LINKS.items()
    )
    return ok, details


SCORING_POINTS = [
    ("issue_set", 2, "Correct transition issue identifier set for PRJ_NIMBUS.", check_issue_set),
    ("ip_domain_transition", 2, "Correct missing trademark license and domain redirect protections.", check_ip_domain),
    (
        "tsa_scope_and_fees",
        3,
        "Correct TSA duration, service scope, fee model, and stranded-cost recovery.",
        check_tsa,
    ),
    ("employee_continuity", 2, "Correct field operations employee continuity and PTO treatment.", check_employee),
    ("tax_allocation", 2, "Correct Section 1060 and transfer-tax allocation package.", check_tax),
    ("deadline_extension", 1, "Correct HSR-driven outside date and seller regulatory extension.", check_deadline),
    ("law_forum", 1, "Correct Delaware governing law and forum fix.", check_law_forum),
    (
        "operational_risk_and_redlines",
        3,
        "Correct operational risk summary, priority order, quantified exposures, and redline package mapping.",
        None,
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
                "goal": goal,
                "weight": weight,
                "assigned_score": weight / max_score,
                "passed": False,
                "earned_score": 0,
                "details": {"error": f"Unable to parse candidate JSON: {exc}"},
            }
            for point_id, weight, goal, _ in SCORING_POINTS
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
            "ip_domain_transition",
            "tsa_scope_and_fees",
            "employee_continuity",
            "deadline_extension",
            "law_forum",
        }:
            passed, details = func(issues, redlines)
        elif point_id == "tax_allocation":
            passed, details = func(redlines)
        else:
            risk_passed, risk_details = check_operational_risk(data)
            redline_passed, redline_details = check_redline_package(redlines)
            passed = risk_passed and redline_passed
            details = {"operational_risk": risk_details, "redline_package": redline_details}

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
