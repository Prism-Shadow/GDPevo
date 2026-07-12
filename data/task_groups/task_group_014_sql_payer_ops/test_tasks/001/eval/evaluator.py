#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED_CASES = {
    "AUTH00013": {
        "first_failure": "none",
        "final_disposition": "ready_for_clinical_review",
        "sla_due_at": "2025-02-17T11:24",
        "sla_rule_used": "TX Medicaid calendar 4 days",
        "sla_source_trace": {
            "state_used": "TX",
            "plan_type_used": "Medicaid",
            "duration_value": 4,
            "duration_unit": "calendar_days",
            "day_type": "calendar",
        },
        "sla_candidate_trace": [
            {
                "state": "TX",
                "plan_type": "Medicaid",
                "duration_value": 4,
                "duration_unit": "calendar_days",
                "computed_due_at": "2025-02-17T11:24",
            }
        ],
        "sla_selection_reason": "single_applicable_rule",
        "gold_card_decision": "not_eligible_plan_or_provider_or_service",
        "queue_destination": "MedImage Review mandatory MD",
        "duplicate_treatment": "no_matching_prior",
        "notice_template": "none_clinical_review",
        "intake_reason_code": "vendor_mandatory_md_review",
        "duplicate_reason_code": "no_prior_match",
        "sla_basis_code": "TX_Medicaid_calendar_4d",
        "intake_source_trace": {
            "service_covered": True,
            "servicing_provider_network_status": "in_network",
            "facility_in_service_area": True,
            "blocking_duplicate_auth_ids": [],
            "ignored_existing_auth_ids": [],
        },
    },
    "AUTH00014": {
        "first_failure": "out_of_network_no_exception",
        "final_disposition": "halted_in_intake",
        "sla_due_at": "2025-02-19T12:31",
        "sla_rule_used": "IL Exchange calendar 5 days",
        "sla_source_trace": {
            "state_used": "IL",
            "plan_type_used": "Exchange",
            "duration_value": 5,
            "duration_unit": "calendar_days",
            "day_type": "calendar",
        },
        "sla_candidate_trace": [
            {
                "state": "IL",
                "plan_type": "Exchange",
                "duration_value": 5,
                "duration_unit": "calendar_days",
                "computed_due_at": "2025-02-19T12:31",
            }
        ],
        "sla_selection_reason": "single_applicable_rule",
        "gold_card_decision": "not_evaluated_due_to_intake_halt",
        "queue_destination": "network_exception_outreach",
        "duplicate_treatment": "not_checked_due_to_earlier_failure",
        "notice_template": "out_of_network_no_exception",
        "intake_reason_code": "servicing_provider_out_of_network_no_exception",
        "duplicate_reason_code": "out_of_network_halt",
        "sla_basis_code": "IL_Exchange_calendar_5d",
        "intake_source_trace": {
            "service_covered": True,
            "servicing_provider_network_status": "out_of_network",
            "facility_in_service_area": True,
            "blocking_duplicate_auth_ids": [],
            "ignored_existing_auth_ids": ["EXA00014"],
        },
    },
    "AUTH00015": {
        "first_failure": "none",
        "final_disposition": "ready_for_clinical_review",
        "sla_due_at": "2025-02-20T13:38",
        "sla_rule_used": "CA Commercial calendar 5 days",
        "sla_source_trace": {
            "state_used": "CA",
            "plan_type_used": "Commercial",
            "duration_value": 5,
            "duration_unit": "calendar_days",
            "day_type": "calendar",
        },
        "sla_candidate_trace": [
            {
                "state": "CA",
                "plan_type": "Commercial",
                "duration_value": 5,
                "duration_unit": "calendar_days",
                "computed_due_at": "2025-02-20T13:38",
            }
        ],
        "sla_selection_reason": "single_applicable_rule",
        "gold_card_decision": "not_eligible_plan_or_provider_or_service",
        "queue_destination": "medical_director_review",
        "duplicate_treatment": "no_matching_prior",
        "notice_template": "none_clinical_review",
        "intake_reason_code": "mandatory_md_review",
        "duplicate_reason_code": "no_prior_match",
        "sla_basis_code": "CA_Commercial_calendar_5d",
        "intake_source_trace": {
            "service_covered": True,
            "servicing_provider_network_status": "in_network",
            "facility_in_service_area": True,
            "blocking_duplicate_auth_ids": [],
            "ignored_existing_auth_ids": [],
        },
    },
    "AUTH00016": {
        "first_failure": "duplicate_authorization",
        "final_disposition": "halted_in_intake",
        "sla_due_at": "2025-02-19T14:45",
        "sla_rule_used": "NY Dual Eligible business 3 days",
        "sla_source_trace": {
            "state_used": "NY",
            "plan_type_used": "Dual Eligible",
            "duration_value": 3,
            "duration_unit": "business_days",
            "day_type": "business",
        },
        "sla_candidate_trace": [
            {
                "state": "NY",
                "plan_type": "Dual Eligible",
                "duration_value": 3,
                "duration_unit": "business_days",
                "computed_due_at": "2025-02-19T14:45",
            }
        ],
        "sla_selection_reason": "single_applicable_rule",
        "gold_card_decision": "not_evaluated_due_to_intake_halt",
        "queue_destination": "duplicate_resolution_queue",
        "duplicate_treatment": "open_overlap_duplicate",
        "notice_template": "duplicate_admin_closure",
        "intake_reason_code": "open_overlap_duplicate",
        "duplicate_reason_code": "open_overlap_duplicate",
        "sla_basis_code": "NY_DualEligible_business_3d",
        "intake_source_trace": {
            "service_covered": True,
            "servicing_provider_network_status": "in_network",
            "facility_in_service_area": True,
            "blocking_duplicate_auth_ids": ["EXA00051"],
            "ignored_existing_auth_ids": ["EXA00016"],
        },
    },
    "AUTH00017": {
        "first_failure": "noncovered_service",
        "final_disposition": "halted_in_intake",
        "sla_due_at": "2025-02-22T15:52",
        "sla_rule_used": "CA Commercial calendar 5 days",
        "sla_source_trace": {
            "state_used": "CA",
            "plan_type_used": "Commercial",
            "duration_value": 5,
            "duration_unit": "calendar_days",
            "day_type": "calendar",
        },
        "sla_candidate_trace": [
            {
                "state": "CA",
                "plan_type": "Commercial",
                "duration_value": 5,
                "duration_unit": "calendar_days",
                "computed_due_at": "2025-02-22T15:52",
            }
        ],
        "sla_selection_reason": "single_applicable_rule",
        "gold_card_decision": "not_evaluated_due_to_intake_halt",
        "queue_destination": "benefit_denial_queue",
        "duplicate_treatment": "not_checked_due_to_earlier_failure",
        "notice_template": "noncovered_benefit",
        "intake_reason_code": "noncovered_benefit",
        "duplicate_reason_code": "benefit_halt",
        "sla_basis_code": "CA_Commercial_calendar_5d",
        "intake_source_trace": {
            "service_covered": False,
            "servicing_provider_network_status": "in_network",
            "facility_in_service_area": True,
            "blocking_duplicate_auth_ids": [],
            "ignored_existing_auth_ids": [],
        },
    },
    "AUTH00018": {
        "first_failure": "noncovered_service",
        "final_disposition": "halted_in_intake",
        "sla_due_at": "2025-02-20T16:59",
        "sla_rule_used": "AZ Commercial calendar 2 days",
        "sla_source_trace": {
            "state_used": "AZ",
            "plan_type_used": "Commercial",
            "duration_value": 2,
            "duration_unit": "calendar_days",
            "day_type": "calendar",
        },
        "sla_candidate_trace": [
            {
                "state": "AZ",
                "plan_type": "Commercial",
                "duration_value": 2,
                "duration_unit": "calendar_days",
                "computed_due_at": "2025-02-20T16:59",
            },
            {
                "state": "NY",
                "plan_type": "Commercial",
                "duration_value": 3,
                "duration_unit": "business_days",
                "computed_due_at": "2025-02-21T16:59",
            },
        ],
        "sla_selection_reason": "earliest_due_at_from_multiple_rules",
        "gold_card_decision": "not_evaluated_due_to_intake_halt",
        "queue_destination": "benefit_denial_queue",
        "duplicate_treatment": "not_checked_due_to_earlier_failure",
        "notice_template": "noncovered_benefit",
        "intake_reason_code": "noncovered_benefit",
        "duplicate_reason_code": "benefit_halt",
        "sla_basis_code": "AZ_Commercial_calendar_2d",
        "intake_source_trace": {
            "service_covered": False,
            "servicing_provider_network_status": "out_of_network",
            "facility_in_service_area": False,
            "blocking_duplicate_auth_ids": [],
            "ignored_existing_auth_ids": [],
        },
    },
}

EXPECTED_METRICS = {
    "ready_for_clinical_review_count": 2,
    "auto_approved_count": 0,
    "duplicate_halt_count": 1,
    "member_or_provider_notice_count": 4,
}


def load_json(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, str(exc)


def normalize_cases(candidate):
    rows = candidate.get("case_outcomes", [])
    if not isinstance(rows, list):
        return {}
    by_id = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("case_id"), str):
            by_id[row["case_id"]] = row
    return by_id


def exact_case_fields(candidate_cases, fields):
    return all(
        case_id in candidate_cases and all(candidate_cases[case_id].get(field) == expected[field] for field in fields)
        for case_id, expected in EXPECTED_CASES.items()
    )


def value_at(node, path):
    current = node
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    if isinstance(current, list):
        if all(isinstance(item, dict) for item in current):
            return sorted(current, key=lambda item: tuple(str(item.get(key)) for key in sorted(item)))
        return sorted(str(item) for item in current)
    return current


def exact_case_paths(candidate_cases, selectors):
    return all(
        case_id in candidate_cases
        and all(value_at(candidate_cases[case_id], path) == value_at(expected, path) for path in selectors.values())
        for case_id, expected in EXPECTED_CASES.items()
    )


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps({"score": 0.0, "max_score": 1.0, "error": "Usage: evaluator.py <candidate.json>", "points": []})
        )
        return 2

    candidate, error = load_json(sys.argv[1])
    if error:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": error, "points": []}))
        return 1

    if not isinstance(candidate, dict):
        print(
            json.dumps(
                {"score": 0.0, "max_score": 1.0, "error": "Candidate root must be a JSON object.", "points": []}
            )
        )
        return 1

    candidate_cases = normalize_cases(candidate)
    metrics = candidate.get("supervisor_metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}

    point_defs = [
        ("SP001_intake_disposition", 2, exact_case_fields(candidate_cases, ["first_failure", "final_disposition"])),
        ("SP002_sla_due_values", 1, exact_case_fields(candidate_cases, ["sla_due_at", "sla_rule_used"])),
        (
            "SP003_gold_card_and_queue",
            1,
            exact_case_fields(candidate_cases, ["gold_card_decision"])
            and exact_case_fields(candidate_cases, ["queue_destination"])
            and metrics.get("auto_approved_count") == EXPECTED_METRICS["auto_approved_count"],
        ),
        (
            "SP004_duplicate_treatment_and_trace",
            3,
            exact_case_fields(candidate_cases, ["duplicate_treatment"])
            and exact_case_paths(
                candidate_cases,
                {
                    "blocking_duplicate_auth_ids": ["intake_source_trace", "blocking_duplicate_auth_ids"],
                    "ignored_existing_auth_ids": ["intake_source_trace", "ignored_existing_auth_ids"],
                },
            )
            and metrics.get("duplicate_halt_count") == EXPECTED_METRICS["duplicate_halt_count"],
        ),
        (
            "SP005_notice_and_ready_summary_metrics",
            1,
            exact_case_fields(candidate_cases, ["notice_template"])
            and metrics.get("member_or_provider_notice_count") == EXPECTED_METRICS["member_or_provider_notice_count"]
            and metrics.get("ready_for_clinical_review_count") == EXPECTED_METRICS["ready_for_clinical_review_count"],
        ),
        (
            "SP006_sla_source_and_candidate_trace",
            3,
            exact_case_paths(
                candidate_cases,
                {
                    "state_used": ["sla_source_trace", "state_used"],
                    "plan_type_used": ["sla_source_trace", "plan_type_used"],
                    "duration_value": ["sla_source_trace", "duration_value"],
                    "duration_unit": ["sla_source_trace", "duration_unit"],
                    "day_type": ["sla_source_trace", "day_type"],
                },
            )
            and exact_case_paths(candidate_cases, {"sla_candidate_trace": ["sla_candidate_trace"]})
            and exact_case_paths(candidate_cases, {"sla_selection_reason": ["sla_selection_reason"]}),
        ),
        (
            "SP007_intake_source_barrier_trace",
            1,
            exact_case_paths(
                candidate_cases,
                {
                    "service_covered": ["intake_source_trace", "service_covered"],
                    "servicing_provider_network_status": ["intake_source_trace", "servicing_provider_network_status"],
                    "facility_in_service_area": ["intake_source_trace", "facility_in_service_area"],
                },
            ),
        ),
        (
            "SP008_intake_reason_codes",
            3,
            exact_case_fields(candidate_cases, ["intake_reason_code"]),
        ),
        (
            "SP009_duplicate_reason_codes",
            3,
            exact_case_fields(candidate_cases, ["duplicate_reason_code"]),
        ),
        (
            "SP010_sla_basis_codes",
            3,
            exact_case_fields(candidate_cases, ["sla_basis_code"]),
        ),
    ]

    raw_score = sum(weight for _name, weight, passed in point_defs if passed)
    raw_max = sum(weight for _name, weight, _passed in point_defs)
    result = {
        "score": raw_score / raw_max,
        "max_score": 1.0,
        "raw_score": raw_score,
        "raw_max_score": raw_max,
        "points": [
            {
                "name": name,
                "weight": weight,
                "earned": weight if passed else 0,
                "passed": bool(passed),
            }
            for name, weight, passed in point_defs
        ],
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
