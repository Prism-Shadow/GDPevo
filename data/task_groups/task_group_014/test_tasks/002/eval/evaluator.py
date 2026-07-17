#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "board_date": "2025-02-27",
    "target_bucket": "test_p2p_batch",
    "p2p_cases": [
        {
            "case_id": "AUTH00019",
            "service_categories": ["Durable Medical Equipment", "Home Health"],
            "p2p_session_status": "completed_with_new_information",
            "criteria_source_ids": ["SRC003"],
            "criteria_source_selection_trace": {
                "selected_source_id": "SRC003",
                "selected_source_name": "Ticonderoga Medical Policy",
                "selected_precedence_rank": 2,
                "excluded_lower_precedence_source_ids": ["SRC004"],
            },
            "final_determination": "partial_approval",
            "overturn_classification": "partial_overturn",
            "letter_queue_category": "partial_approval_with_appeal_rights",
            "adverse_authority_status": "md_only_adverse_final",
            "final_rationale_code": "SRC003_partial_clinical_support_after_p2p",
            "letter_authority_reason_code": "partial_approval_with_appeal_rights__md_only_adverse_final__SRC003_partial_clinical_support_after_p2p",
            "criteria_gap_keys": [
                "diagnosis_confirmed",
                "equipment_trial_needed",
                "face_to_face_documented",
                "physician_plan",
                "skilled_need",
            ],
            "p2p_source_trace": {
                "p2p_id": "P2P00019",
                "requesting_provider_joined": True,
                "new_information": True,
                "source_outcome": "no_show",
                "duration_minutes": 20,
            },
            "review_event_trace": {
                "medical_director_event_ids": ["EVT00019_2"],
                "medical_director_outcomes": ["adverse_pending"],
            },
            "admin_source_trace": {
                "facility_in_service_area": True,
                "oon_exception": False,
                "mandatory_md_review": False,
            },
            "additional_info_needed": False,
            "appeal_rights_notice": True,
        },
        {
            "case_id": "AUTH00020",
            "service_categories": ["Physical Therapy"],
            "p2p_session_status": "completed_no_new_information",
            "criteria_source_ids": ["SRC003"],
            "criteria_source_selection_trace": {
                "selected_source_id": "SRC003",
                "selected_source_name": "Ticonderoga Medical Policy",
                "selected_precedence_rank": 2,
                "excluded_lower_precedence_source_ids": ["SRC004"],
            },
            "final_determination": "denied_upheld",
            "overturn_classification": "upheld",
            "letter_queue_category": "denial_upheld_with_appeal_rights",
            "adverse_authority_status": "md_only_adverse_final",
            "final_rationale_code": "SRC003_criteria_not_clearly_met_no_new_info",
            "letter_authority_reason_code": "denial_upheld_with_appeal_rights__md_only_adverse_final__SRC003_criteria_not_clearly_met_no_new_info",
            "criteria_gap_keys": ["functional_limitation", "measurable_progress"],
            "p2p_source_trace": {
                "p2p_id": "P2P00020",
                "requesting_provider_joined": True,
                "new_information": False,
                "source_outcome": "no_show",
                "duration_minutes": 16,
            },
            "review_event_trace": {
                "medical_director_event_ids": [],
                "medical_director_outcomes": [],
            },
            "admin_source_trace": {
                "facility_in_service_area": True,
                "oon_exception": False,
                "mandatory_md_review": False,
            },
            "additional_info_needed": False,
            "appeal_rights_notice": True,
        },
        {
            "case_id": "AUTH00021",
            "service_categories": ["Physical Therapy"],
            "p2p_session_status": "not_completed_additional_information_requested",
            "criteria_source_ids": ["SRC003"],
            "criteria_source_selection_trace": {
                "selected_source_id": "SRC003",
                "selected_source_name": "Ticonderoga Medical Policy",
                "selected_precedence_rank": 2,
                "excluded_lower_precedence_source_ids": ["SRC004"],
            },
            "final_determination": "pending_additional_information",
            "overturn_classification": "not_finalized",
            "letter_queue_category": "additional_information_request",
            "adverse_authority_status": "no_adverse_final_pending_info",
            "final_rationale_code": "SRC003_criteria_not_clearly_met_more_information_needed",
            "letter_authority_reason_code": "additional_information_request__no_adverse_final_pending_info__SRC003_criteria_not_clearly_met_more_information_needed",
            "criteria_gap_keys": ["functional_limitation", "measurable_progress", "plan_of_care"],
            "p2p_source_trace": {
                "p2p_id": "P2P00021",
                "requesting_provider_joined": True,
                "new_information": False,
                "source_outcome": "additional_info_requested",
                "duration_minutes": 22,
            },
            "review_event_trace": {
                "medical_director_event_ids": ["EVT00021_2"],
                "medical_director_outcomes": ["approve"],
            },
            "admin_source_trace": {
                "facility_in_service_area": True,
                "oon_exception": False,
                "mandatory_md_review": False,
            },
            "additional_info_needed": True,
            "appeal_rights_notice": False,
        },
        {
            "case_id": "AUTH00022",
            "service_categories": ["Physical Therapy"],
            "p2p_session_status": "completed_provider_no_show",
            "criteria_source_ids": ["SRC003"],
            "criteria_source_selection_trace": {
                "selected_source_id": "SRC003",
                "selected_source_name": "Ticonderoga Medical Policy",
                "selected_precedence_rank": 2,
                "excluded_lower_precedence_source_ids": ["SRC004"],
            },
            "final_determination": "denied_upheld",
            "overturn_classification": "upheld",
            "letter_queue_category": "denial_upheld_with_appeal_rights",
            "adverse_authority_status": "md_only_adverse_final",
            "final_rationale_code": "SRC003_provider_no_show_criteria_not_clearly_met",
            "letter_authority_reason_code": "denial_upheld_with_appeal_rights__md_only_adverse_final__SRC003_provider_no_show_criteria_not_clearly_met",
            "criteria_gap_keys": ["measurable_progress", "plan_of_care"],
            "p2p_source_trace": {
                "p2p_id": "P2P00022",
                "requesting_provider_joined": False,
                "new_information": True,
                "source_outcome": "upheld",
                "duration_minutes": 8,
            },
            "review_event_trace": {
                "medical_director_event_ids": [],
                "medical_director_outcomes": [],
            },
            "admin_source_trace": {
                "facility_in_service_area": True,
                "oon_exception": False,
                "mandatory_md_review": False,
            },
            "additional_info_needed": False,
            "appeal_rights_notice": True,
        },
        {
            "case_id": "AUTH00023",
            "service_categories": ["Advanced Imaging"],
            "p2p_session_status": "completed_no_new_information",
            "criteria_source_ids": ["SRC003"],
            "criteria_source_selection_trace": {
                "selected_source_id": "SRC003",
                "selected_source_name": "Ticonderoga Medical Policy",
                "selected_precedence_rank": 2,
                "excluded_lower_precedence_source_ids": ["SRC004"],
            },
            "final_determination": "pending_additional_information",
            "overturn_classification": "not_finalized",
            "letter_queue_category": "additional_information_request",
            "adverse_authority_status": "mandatory_md_review_pending_info",
            "final_rationale_code": "SRC003_mandatory_md_more_information_needed",
            "letter_authority_reason_code": "additional_information_request__mandatory_md_review_pending_info__SRC003_mandatory_md_more_information_needed",
            "criteria_gap_keys": ["prior_imaging_reviewed", "red_flag_symptoms"],
            "p2p_source_trace": {
                "p2p_id": "P2P00023",
                "requesting_provider_joined": True,
                "new_information": False,
                "source_outcome": "no_show",
                "duration_minutes": 15,
            },
            "review_event_trace": {
                "medical_director_event_ids": ["EVT00023_2"],
                "medical_director_outcomes": ["request_more_info"],
            },
            "admin_source_trace": {
                "facility_in_service_area": True,
                "oon_exception": True,
                "mandatory_md_review": True,
            },
            "additional_info_needed": True,
            "appeal_rights_notice": False,
        },
        {
            "case_id": "AUTH00024",
            "service_categories": ["Cardiology Imaging"],
            "p2p_session_status": "completed_no_new_information",
            "criteria_source_ids": ["SRC003"],
            "criteria_source_selection_trace": {
                "selected_source_id": "SRC003",
                "selected_source_name": "Ticonderoga Medical Policy",
                "selected_precedence_rank": 2,
                "excluded_lower_precedence_source_ids": ["SRC004"],
            },
            "final_determination": "direct_administrative_denial",
            "overturn_classification": "direct_denial_exempt",
            "letter_queue_category": "administrative_denial_with_appeal_rights",
            "adverse_authority_status": "direct_admin_final",
            "final_rationale_code": "SRC003_direct_admin_out_of_service_area",
            "letter_authority_reason_code": "administrative_denial_with_appeal_rights__direct_admin_final__SRC003_direct_admin_out_of_service_area",
            "criteria_gap_keys": [
                "known_cad_or_high_risk",
                "management_change_expected",
                "stress_test_inconclusive",
            ],
            "p2p_source_trace": {
                "p2p_id": "P2P00024",
                "requesting_provider_joined": True,
                "new_information": False,
                "source_outcome": "no_show",
                "duration_minutes": 15,
            },
            "review_event_trace": {
                "medical_director_event_ids": [],
                "medical_director_outcomes": [],
            },
            "admin_source_trace": {
                "facility_in_service_area": False,
                "oon_exception": True,
                "mandatory_md_review": True,
            },
            "additional_info_needed": False,
            "appeal_rights_notice": True,
        },
    ],
    "finalization_counts": {
        "approved_count": 0,
        "partial_approval_count": 1,
        "denied_or_upheld_count": 2,
        "direct_admin_denial_count": 1,
        "additional_info_needed_count": 2,
        "appeal_rights_notice_count": 4,
    },
    "letter_queue": {
        "approval": [],
        "partial_approval_with_appeal_rights": ["AUTH00019"],
        "denial_upheld_with_appeal_rights": ["AUTH00020", "AUTH00022"],
        "administrative_denial_with_appeal_rights": ["AUTH00024"],
        "additional_information_request": ["AUTH00021", "AUTH00023"],
    },
}


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_list(value):
    if not isinstance(value, list):
        return value
    return sorted(str(item) for item in value)


def normalize_queue(value):
    if not isinstance(value, dict):
        return {}
    return {str(key): normalize_list(items) for key, items in value.items()}


def case_map(doc):
    rows = doc.get("p2p_cases", [])
    if not isinstance(rows, list):
        return {}
    return {str(row.get("case_id")): row for row in rows if isinstance(row, dict)}


def field_map(doc, fields):
    result = {}
    for case_id, row in case_map(doc).items():
        result[case_id] = {}
        for field in fields:
            value = row.get(field)
            if field in {"service_categories", "criteria_source_ids", "criteria_gap_keys"}:
                value = normalize_list(value)
            result[case_id][field] = value
    return result


def expected_field_map(fields):
    return field_map(EXPECTED, fields)


def add_point(points, name, weight, passed, expected=None, actual=None):
    points.append(
        {
            "name": name,
            "weight": weight,
            "earned": weight if passed else 0,
            "passed": bool(passed),
            "expected": expected,
            "actual": actual,
        }
    )


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": 1,
                    "raw_score": 0,
                    "max_raw_score": 20,
                    "error": "usage: evaluator.py <candidate.json>",
                    "points": [],
                }
            )
        )
        return 2

    try:
        candidate = load_json(sys.argv[1])
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": 1,
                    "raw_score": 0,
                    "max_raw_score": 20,
                    "error": f"invalid JSON: {exc}",
                    "points": [],
                }
            )
        )
        return 1

    if not isinstance(candidate, dict):
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": 1,
                    "raw_score": 0,
                    "max_raw_score": 20,
                    "error": "candidate root must be an object",
                    "points": [],
                }
            )
        )
        return 1

    points = []
    expected_cases = sorted(case_map(EXPECTED))
    actual_cases = sorted(case_map(candidate))
    case_set_ok = actual_cases == expected_cases

    add_point(
        points,
        "SP001_board_classifications_by_case",
        1,
        case_set_ok
        and field_map(candidate, ["final_determination", "p2p_session_status"])
        == expected_field_map(["final_determination", "p2p_session_status"])
        and field_map(candidate, ["overturn_classification"]) == expected_field_map(["overturn_classification"])
        and field_map(candidate, ["letter_queue_category"]) == expected_field_map(["letter_queue_category"])
        and field_map(candidate, ["adverse_authority_status"]) == expected_field_map(["adverse_authority_status"]),
        {
            "final_determination": expected_field_map(["final_determination", "p2p_session_status"]),
            "overturn_classification": expected_field_map(["overturn_classification"]),
            "letter_queue_category": expected_field_map(["letter_queue_category"]),
            "adverse_authority_status": expected_field_map(["adverse_authority_status"]),
        },
        {
            "final_determination": field_map(candidate, ["final_determination", "p2p_session_status"]),
            "overturn_classification": field_map(candidate, ["overturn_classification"]),
            "letter_queue_category": field_map(candidate, ["letter_queue_category"]),
            "adverse_authority_status": field_map(candidate, ["adverse_authority_status"]),
        },
    )
    add_point(
        points,
        "SP005_criteria_source_and_gap_keys",
        2,
        case_set_ok
        and field_map(candidate, ["criteria_source_ids", "criteria_gap_keys"])
        == expected_field_map(["criteria_source_ids", "criteria_gap_keys"]),
        expected_field_map(["criteria_source_ids", "criteria_gap_keys"]),
        field_map(candidate, ["criteria_source_ids", "criteria_gap_keys"]),
    )
    add_point(
        points,
        "SP006_p2p_and_review_event_trace",
        3,
        case_set_ok
        and field_map(candidate, ["p2p_source_trace"]) == expected_field_map(["p2p_source_trace"])
        and field_map(candidate, ["review_event_trace"]) == expected_field_map(["review_event_trace"]),
        {
            "p2p_source_trace": expected_field_map(["p2p_source_trace"]),
            "review_event_trace": expected_field_map(["review_event_trace"]),
        },
        {
            "p2p_source_trace": field_map(candidate, ["p2p_source_trace"]),
            "review_event_trace": field_map(candidate, ["review_event_trace"]),
        },
    )
    add_point(
        points,
        "SP007_additional_information_and_appeal_notice_cases",
        1,
        case_set_ok
        and field_map(candidate, ["additional_info_needed"]) == expected_field_map(["additional_info_needed"])
        and field_map(candidate, ["appeal_rights_notice"]) == expected_field_map(["appeal_rights_notice"])
        and candidate.get("finalization_counts", {}).get("additional_info_needed_count")
        == EXPECTED["finalization_counts"]["additional_info_needed_count"]
        and candidate.get("finalization_counts", {}).get("appeal_rights_notice_count")
        == EXPECTED["finalization_counts"]["appeal_rights_notice_count"],
        {
            "additional_info": expected_field_map(["additional_info_needed"]),
            "appeal_notice": expected_field_map(["appeal_rights_notice"]),
            "additional_info_count": EXPECTED["finalization_counts"]["additional_info_needed_count"],
            "appeal_notice_count": EXPECTED["finalization_counts"]["appeal_rights_notice_count"],
        },
        {
            "additional_info": field_map(candidate, ["additional_info_needed"]),
            "appeal_notice": field_map(candidate, ["appeal_rights_notice"]),
            "additional_info_count": candidate.get("finalization_counts", {}).get("additional_info_needed_count")
            if isinstance(candidate.get("finalization_counts"), dict)
            else None,
            "appeal_notice_count": candidate.get("finalization_counts", {}).get("appeal_rights_notice_count")
            if isinstance(candidate.get("finalization_counts"), dict)
            else None,
        },
    )
    add_point(
        points,
        "SP008_finalization_counts_and_letter_queue",
        1,
        candidate.get("board_date") == EXPECTED["board_date"]
        and candidate.get("target_bucket") == EXPECTED["target_bucket"]
        and candidate.get("finalization_counts") == EXPECTED["finalization_counts"]
        and normalize_queue(candidate.get("letter_queue")) == normalize_queue(EXPECTED["letter_queue"]),
        {
            "board_date": EXPECTED["board_date"],
            "target_bucket": EXPECTED["target_bucket"],
            "finalization_counts": EXPECTED["finalization_counts"],
            "letter_queue": EXPECTED["letter_queue"],
        },
        {
            "board_date": candidate.get("board_date"),
            "target_bucket": candidate.get("target_bucket"),
            "finalization_counts": candidate.get("finalization_counts"),
            "letter_queue": candidate.get("letter_queue"),
        },
    )
    add_point(
        points,
        "SP009_admin_source_trace",
        1,
        case_set_ok and field_map(candidate, ["admin_source_trace"]) == expected_field_map(["admin_source_trace"]),
        expected_field_map(["admin_source_trace"]),
        field_map(candidate, ["admin_source_trace"]),
    )
    add_point(
        points,
        "SP010_criteria_source_selection_trace",
        2,
        case_set_ok
        and field_map(candidate, ["criteria_source_selection_trace"])
        == expected_field_map(["criteria_source_selection_trace"]),
        expected_field_map(["criteria_source_selection_trace"]),
        field_map(candidate, ["criteria_source_selection_trace"]),
    )
    add_point(
        points,
        "SP011_final_rationale_code",
        3,
        case_set_ok and field_map(candidate, ["final_rationale_code"]) == expected_field_map(["final_rationale_code"]),
        expected_field_map(["final_rationale_code"]),
        field_map(candidate, ["final_rationale_code"]),
    )
    add_point(
        points,
        "SP012_finalization_reason_bundle",
        3,
        case_set_ok
        and field_map(candidate, ["final_rationale_code"]) == expected_field_map(["final_rationale_code"])
        and field_map(candidate, ["adverse_authority_status"]) == expected_field_map(["adverse_authority_status"])
        and field_map(candidate, ["letter_queue_category"]) == expected_field_map(["letter_queue_category"]),
        {
            "final_rationale_code": expected_field_map(["final_rationale_code"]),
            "adverse_authority_status": expected_field_map(["adverse_authority_status"]),
            "letter_queue_category": expected_field_map(["letter_queue_category"]),
        },
        {
            "final_rationale_code": field_map(candidate, ["final_rationale_code"]),
            "adverse_authority_status": field_map(candidate, ["adverse_authority_status"]),
            "letter_queue_category": field_map(candidate, ["letter_queue_category"]),
        },
    )
    add_point(
        points,
        "SP013_letter_authority_reason_codes",
        3,
        case_set_ok
        and field_map(candidate, ["letter_authority_reason_code"])
        == expected_field_map(["letter_authority_reason_code"]),
        expected_field_map(["letter_authority_reason_code"]),
        field_map(candidate, ["letter_authority_reason_code"]),
    )

    raw_score = sum(point["earned"] for point in points)
    max_raw_score = sum(point["weight"] for point in points)
    result = {
        "score": raw_score / max_raw_score,
        "max_score": 1,
        "raw_score": raw_score,
        "max_raw_score": max_raw_score,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
