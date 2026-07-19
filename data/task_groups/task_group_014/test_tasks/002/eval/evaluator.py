#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "case_id": "APPEAL-TE-002",
    "appeal_id": "APL-TE-002",
    "drug": "Dupixent",
    "appeal_path": "expedited_internal",
    "expedited": True,
    "expedited_basis": "provider_attested_serious_health_risk",
    "appeal_deadline": "2026-06-09",
    "owner": "appeals-rx",
    "documented_failures": {
        "topical tacrolimus",
        "phototherapy",
    },
    "assistance": {
        "program_name": "Dupixent MyWay",
        "status": "eligible_missing_information",
        "missing_fields": {
            "household_income_proof",
        },
    },
    "required_packet_items": {
        "denial_notice",
        "member_authorization",
        "prescriber_rationale",
        "formulary_failure_evidence",
        "household_income_proof",
    },
    "missing_packet_items": {
        "household_income_proof",
    },
    "next_action": "complete_expedited_appeal_and_request_income_proof",
    "basis_audit": {
        "source_precedence": "payer_appeal_before_manufacturer_assistance",
        "precedence_record_order": [
            "apl-te-002",
            "trial-te-002-1",
            "trial-te-002-2",
            "household_income_proof",
        ],
        "controlling_record_ids": [
            "apl-te-002",
            "trial-te-002-1",
            "trial-te-002-2",
        ],
        "exception_record_ids": [
            "household_income_proof",
        ],
    },
}


RUBRIC = [
    (
        "target_appeal_drug_owner",
        1,
        "Correct target appeal, drug, and owner.",
    ),
    (
        "expedited_internal_path_basis_deadline",
        3,
        "Correct expedited internal path, expedited basis, and appeal deadline.",
    ),
    (
        "documented_failure_set",
        2,
        "Correct documented prior therapy failure set.",
    ),
    (
        "assistance_program_status_and_gap",
        2,
        "Correct assistance program, normalized status, and missing income proof.",
    ),
    (
        "required_and_missing_packet_sets",
        2,
        "Correct required packet set and missing packet set.",
    ),
    (
        "next_action",
        1,
        "Correct next action preserving the appeal versus assistance distinction.",
    ),
    (
        "basis_source_precedence",
        3,
        "Correct business source-precedence basis.",
    ),
    (
        "basis_precedence_record_order",
        3,
        "Correct source-precedence record order.",
    ),
    (
        "basis_controlling_records",
        1,
        "Correct controlling appeal and trial record IDs.",
    ),
    (
        "basis_exception_records",
        2,
        "Correct assistance exception and gap IDs.",
    ),
]


def load_answer(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            answer = json.load(handle)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(answer, dict):
        return None, "Submitted answer must be a JSON object."
    return answer, None


def clean_str(value, lower=False, upper=False):
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    if lower:
        return text.lower()
    if upper:
        return text.upper()
    return text


def clean_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def get_value(answer, *path):
    value = answer
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def normalized_set(value, lower=False, upper=False):
    if not isinstance(value, list):
        return None
    result = set()
    for item in value:
        text = clean_str(item, lower=lower, upper=upper)
        if text is None:
            return None
        result.add(text)
    return result


def normalized_list(value, lower=False, upper=False):
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        text = clean_str(item, lower=lower, upper=upper)
        if text is None:
            return None
        result.append(text)
    return result


def audit_value(answer, key):
    audit = answer.get("basis_audit")
    if not isinstance(audit, dict):
        return None
    return audit.get(key)


def check_identity(answer):
    return (
        clean_str(answer.get("case_id"), upper=True) == EXPECTED["case_id"]
        and clean_str(answer.get("appeal_id"), upper=True) == EXPECTED["appeal_id"]
        and clean_str(answer.get("drug")) == EXPECTED["drug"]
        and clean_str(answer.get("owner"), lower=True) == EXPECTED["owner"]
    )


def check_expedited_path(answer):
    return (
        clean_str(answer.get("appeal_path"), lower=True) == EXPECTED["appeal_path"]
        and clean_bool(answer.get("expedited")) is EXPECTED["expedited"]
        and clean_str(answer.get("expedited_basis"), lower=True) == EXPECTED["expedited_basis"]
        and clean_str(answer.get("appeal_deadline")) == EXPECTED["appeal_deadline"]
    )


def check_documented_failures(answer):
    return normalized_set(answer.get("documented_failures"), lower=True) == EXPECTED["documented_failures"]


def check_assistance(answer):
    return (
        clean_str(get_value(answer, "assistance", "program_name")) == EXPECTED["assistance"]["program_name"]
        and clean_str(get_value(answer, "assistance", "status"), lower=True) == EXPECTED["assistance"]["status"]
        and normalized_set(get_value(answer, "assistance", "missing_fields"), lower=True)
        == EXPECTED["assistance"]["missing_fields"]
    )


def check_packet(answer):
    return (
        normalized_set(answer.get("required_packet_items"), lower=True) == EXPECTED["required_packet_items"]
        and normalized_set(answer.get("missing_packet_items"), lower=True) == EXPECTED["missing_packet_items"]
    )


def check_next_action(answer):
    return clean_str(answer.get("next_action"), lower=True) == EXPECTED["next_action"]


def check_basis_source_precedence(answer):
    return (
        clean_str(audit_value(answer, "source_precedence"), lower=True) == EXPECTED["basis_audit"]["source_precedence"]
    )


def check_basis_controlling_records(answer):
    return (
        normalized_list(audit_value(answer, "controlling_record_ids"), lower=True)
        == EXPECTED["basis_audit"]["controlling_record_ids"]
    )


def check_basis_precedence_record_order(answer):
    return (
        normalized_list(audit_value(answer, "precedence_record_order"), lower=True)
        == EXPECTED["basis_audit"]["precedence_record_order"]
    )


def check_basis_exception_records(answer):
    return (
        normalized_list(audit_value(answer, "exception_record_ids"), lower=True)
        == EXPECTED["basis_audit"]["exception_record_ids"]
    )


CHECKS = {
    "target_appeal_drug_owner": check_identity,
    "expedited_internal_path_basis_deadline": check_expedited_path,
    "documented_failure_set": check_documented_failures,
    "assistance_program_status_and_gap": check_assistance,
    "required_and_missing_packet_sets": check_packet,
    "next_action": check_next_action,
    "basis_source_precedence": check_basis_source_precedence,
    "basis_precedence_record_order": check_basis_precedence_record_order,
    "basis_controlling_records": check_basis_controlling_records,
    "basis_exception_records": check_basis_exception_records,
}


DETAILS = {
    "target_appeal_drug_owner": {
        "expected_case_id": EXPECTED["case_id"],
        "expected_appeal_id": EXPECTED["appeal_id"],
        "expected_drug": EXPECTED["drug"],
        "expected_owner": EXPECTED["owner"],
    },
    "expedited_internal_path_basis_deadline": {
        "expected_appeal_path": EXPECTED["appeal_path"],
        "expected_expedited": EXPECTED["expedited"],
        "expected_expedited_basis": EXPECTED["expedited_basis"],
        "expected_appeal_deadline": EXPECTED["appeal_deadline"],
    },
    "documented_failure_set": {
        "expected_documented_failures": sorted(EXPECTED["documented_failures"]),
    },
    "assistance_program_status_and_gap": {
        "expected_program_name": EXPECTED["assistance"]["program_name"],
        "expected_status": EXPECTED["assistance"]["status"],
        "expected_missing_fields": sorted(EXPECTED["assistance"]["missing_fields"]),
    },
    "required_and_missing_packet_sets": {
        "expected_required_packet_items": sorted(EXPECTED["required_packet_items"]),
        "expected_missing_packet_items": sorted(EXPECTED["missing_packet_items"]),
    },
    "next_action": {
        "expected_next_action": EXPECTED["next_action"],
    },
    "basis_source_precedence": {
        "expected_source_precedence": EXPECTED["basis_audit"]["source_precedence"],
    },
    "basis_precedence_record_order": {
        "expected_precedence_record_order": EXPECTED["basis_audit"]["precedence_record_order"],
    },
    "basis_controlling_records": {
        "expected_controlling_record_ids": EXPECTED["basis_audit"]["controlling_record_ids"],
    },
    "basis_exception_records": {
        "expected_exception_record_ids": EXPECTED["basis_audit"]["exception_record_ids"],
    },
}


def empty_result(error):
    total_weight = sum(weight for _, weight, _ in RUBRIC)
    return {
        "score": 0.0,
        "points": [
            {
                "name": name,
                "goal": goal,
                "weight": weight,
                "assigned_score": weight / total_weight,
                "passed": False,
                "earned_score": 0.0,
                "details": {"error": error},
            }
            for name, weight, goal in RUBRIC
        ],
        "total_weight": total_weight,
    }


def evaluate(answer):
    total_weight = sum(weight for _, weight, _ in RUBRIC)
    points = []
    earned_weight = 0
    for name, weight, goal in RUBRIC:
        passed = bool(CHECKS[name](answer))
        if passed:
            earned_weight += weight
        assigned_score = weight / total_weight
        points.append(
            {
                "name": name,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned_score,
                "passed": passed,
                "earned_score": assigned_score if passed else 0.0,
                "details": DETAILS[name],
            }
        )
    return {
        "score": earned_weight / total_weight,
        "points": points,
        "total_weight": total_weight,
    }


def main():
    answer_path = (
        sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    )
    answer, error = load_answer(answer_path)
    if error is not None:
        print(json.dumps(empty_result(error), indent=2, sort_keys=True))
        return
    print(json.dumps(evaluate(answer), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
