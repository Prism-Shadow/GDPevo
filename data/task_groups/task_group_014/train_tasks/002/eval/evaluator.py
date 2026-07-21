#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "case_id": "APPEAL-TR-002",
    "appeal_id": "APL-TR-002",
    "drug": "Vraylar",
    "appeal_path": "standard_internal",
    "expedited": False,
    "appeal_deadline": "2026-06-07",
    "owner": "appeals-rx",
    "documented_failures": ["quetiapine"],
    "undocumented_or_insufficient_failures": ["lurasidone"],
    "criteria_results": {
        "DRUG-AUTH": "met",
        "DRUG-DENIAL": "met",
        "DRUG-RATIONALE": "met",
        "DRUG-FAILURES": "partial",
    },
    "required_packet_items": [
        "denial_notice",
        "member_authorization",
        "prescriber_rationale",
        "formulary_failure_evidence",
        "household_income_proof",
    ],
    "missing_packet_items": [
        "lurasidone_fill_record",
        "household_income_proof",
    ],
    "assistance": {
        "program_name": "Vraylar Connect",
        "status": "eligible_missing_information",
        "missing_fields": ["household_income_proof"],
    },
    "next_action": "request_more_information",
    "basis_audit": {
        "source_precedence": "payer_appeal_before_manufacturer_assistance",
        "precedence_record_order": ["apl-tr-002", "trial-tr-002-1", "trial-tr-002-2", "household_income_proof"],
        "controlling_record_ids": ["apl-tr-002", "trial-tr-002-1"],
        "exception_record_ids": ["trial-tr-002-2", "household_income_proof"],
    },
}


def load_answer(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def get_value(answer, *path):
    value = answer
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def normalize_string(value):
    if not isinstance(value, str):
        return value
    return " ".join(value.strip().lower().split())


def normalize_list(value):
    if not isinstance(value, list):
        return None
    return sorted(normalize_string(item) for item in value)


def normalize_ordered_list(value):
    if not isinstance(value, list):
        return None
    return [normalize_string(item) for item in value]


def list_set_equals(answer, key, expected):
    return normalize_list(answer.get(key)) == sorted(expected)


def nested_list_set_equals(answer, path, expected):
    return normalize_list(get_value(answer, *path)) == sorted(expected)


def check_identity(answer):
    return (
        answer.get("case_id") == EXPECTED["case_id"]
        and answer.get("appeal_id") == EXPECTED["appeal_id"]
        and answer.get("drug") == EXPECTED["drug"]
        and answer.get("owner") == EXPECTED["owner"]
    )


def check_path_deadline(answer):
    return (
        answer.get("appeal_path") == EXPECTED["appeal_path"]
        and answer.get("expedited") is EXPECTED["expedited"]
        and answer.get("appeal_deadline") == EXPECTED["appeal_deadline"]
    )


def check_drug_trials(answer):
    return list_set_equals(answer, "documented_failures", EXPECTED["documented_failures"]) and list_set_equals(
        answer,
        "undocumented_or_insufficient_failures",
        EXPECTED["undocumented_or_insufficient_failures"],
    )


def check_criteria(answer):
    criteria = answer.get("criteria_results")
    return isinstance(criteria, dict) and criteria == EXPECTED["criteria_results"]


def check_required_packet(answer):
    return list_set_equals(answer, "required_packet_items", EXPECTED["required_packet_items"])


def check_missing_packet_and_assistance_gap(answer):
    return list_set_equals(
        answer, "missing_packet_items", EXPECTED["missing_packet_items"]
    ) and nested_list_set_equals(
        answer,
        ("assistance", "missing_fields"),
        EXPECTED["assistance"]["missing_fields"],
    )


def check_next_action_and_assistance(answer):
    return (
        get_value(answer, "assistance", "program_name") == EXPECTED["assistance"]["program_name"]
        and get_value(answer, "assistance", "status") == EXPECTED["assistance"]["status"]
        and answer.get("next_action") == EXPECTED["next_action"]
    )


def check_basis_audit(answer):
    audit = answer.get("basis_audit") if isinstance(answer, dict) else None
    if not isinstance(audit, dict):
        return False
    actual = {
        "source_precedence": normalize_string(audit.get("source_precedence")),
        "precedence_record_order": normalize_ordered_list(audit.get("precedence_record_order")),
        "controlling_record_ids": normalize_ordered_list(audit.get("controlling_record_ids")),
        "exception_record_ids": normalize_ordered_list(audit.get("exception_record_ids")),
    }
    return actual == EXPECTED["basis_audit"]


RUBRIC = [
    {
        "id": "identity",
        "goal": "Correct target appeal, drug, and owner.",
        "weight": 1,
        "check": check_identity,
    },
    {
        "id": "appeal_path_deadline",
        "goal": "Correct standard internal non-expedited appeal path and deadline.",
        "weight": 2,
        "check": check_path_deadline,
    },
    {
        "id": "drug_trial_distinction",
        "goal": "Correct documented versus insufficient drug-trial distinction.",
        "weight": 2,
        "check": check_drug_trials,
    },
    {
        "id": "criteria_results",
        "goal": "Correct criteria result map including DRUG-FAILURES as partial.",
        "weight": 2,
        "check": check_criteria,
    },
    {
        "id": "required_packet",
        "goal": "Correct required packet set.",
        "weight": 1,
        "check": check_required_packet,
    },
    {
        "id": "missing_packet_and_income_gap",
        "goal": "Correct missing packet items and assistance missing income proof.",
        "weight": 2,
        "check": check_missing_packet_and_assistance_gap,
    },
    {
        "id": "next_action_assistance_status",
        "goal": "Correct next action, assistance program, and assistance status.",
        "weight": 1,
        "check": check_next_action_and_assistance,
    },
    {
        "id": "business_basis_audit",
        "goal": "Correct business basis-audit source, controlling records, and exception records.",
        "weight": 1,
        "check": check_basis_audit,
    },
]


def evaluate(answer):
    total_weight = sum(point["weight"] for point in RUBRIC)
    results = []
    earned_weight = 0
    for point in RUBRIC:
        passed = bool(point["check"](answer))
        earned = point["weight"] if passed else 0
        earned_weight += earned
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": point["weight"] / total_weight,
                "passed": passed,
                "earned_score": earned / total_weight,
            }
        )
    return {
        "score": earned_weight / total_weight,
        "points": results,
        "total_weight": total_weight,
    }


def main():
    answer_path = (
        sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    )
    answer, error = load_answer(answer_path)
    if error is not None or not isinstance(answer, dict):
        total_weight = sum(point["weight"] for point in RUBRIC)
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "points": [
                        {
                            "id": point["id"],
                            "goal": point["goal"],
                            "weight": point["weight"],
                            "assigned_score": point["weight"] / total_weight,
                            "passed": False,
                            "earned_score": 0.0,
                        }
                        for point in RUBRIC
                    ],
                    "total_weight": total_weight,
                    "error": error or "Submitted answer must be a JSON object.",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    print(json.dumps(evaluate(answer), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
