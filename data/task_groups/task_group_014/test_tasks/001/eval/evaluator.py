#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "case_id": "CASE-TE-001",
    "recommendation": "pend_for_information",
    "final_status": "pended",
    "route": "request_more_information",
    "requested_cpt": "92507",
    "modifier": "GN",
    "requested_units": 16,
    "approved_units": 0,
    "criteria_results": {
        "ST-POC": "not_met",
        "ST-CONFLICT": "not_met",
    },
    "missing_information": {
        "clarified_frequency",
        "duration_weeks",
        "reconcile_note_plan_conflict",
    },
    "evidence_documents": [
        "DOC-TE-001-NOTE",
        "DOC-TE-001-POC",
    ],
    "excluded_documents": [
        "DOC-TE-001-STALE",
    ],
    "due_date": "2026-06-09",
    "basis_audit": {
        "source_precedence": "current_clinical_records_over_stale_export",
        "precedence_record_order": [
            "doc-te-001-note",
            "doc-te-001-poc",
            "doc-te-001-stale",
        ],
        "controlling_record_ids": [
            "doc-te-001-note",
            "doc-te-001-poc",
        ],
        "exception_record_ids": [
            "st-poc",
            "st-conflict",
            "doc-te-001-stale",
        ],
    },
}


RUBRIC = [
    (
        "target_case_and_requested_speech_service",
        1,
        "Correct target case and speech CPT, modifier, and requested units.",
    ),
    (
        "pend_disposition_and_route",
        3,
        "Correct pend-for-information recommendation, final status, and route.",
    ),
    (
        "speech_therapy_criteria_results",
        2,
        "Correct criteria result map for ST-POC and ST-CONFLICT.",
    ),
    (
        "missing_information_set",
        2,
        "Correct missing-information set.",
    ),
    (
        "current_evidence_and_stale_exclusion",
        2,
        "Correct current evidence documents and stale exclusion.",
    ),
    (
        "approved_units_and_due_date",
        1,
        "Correct zero approved units and due date.",
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
        "Correct controlling business record IDs.",
    ),
    (
        "basis_exception_records",
        2,
        "Correct exception, gap, and excluded-record IDs.",
    ),
]


def clean_str(value, upper=False, lower=False):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if upper:
        return text.upper()
    if lower:
        return text.lower()
    return text


def as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit()):
            return int(stripped)
    return None


def normalized_set(value, upper=False, lower=False):
    if not isinstance(value, list):
        return None
    result = set()
    for item in value:
        text = clean_str(item, upper=upper, lower=lower)
        if text is None:
            return None
        result.add(text)
    return result


def normalized_list(value, upper=False, lower=False):
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        text = clean_str(item, upper=upper, lower=lower)
        if text is None:
            return None
        result.append(text)
    return result


def normalized_criteria(value):
    if isinstance(value, dict):
        pairs = value.items()
    elif isinstance(value, list):
        pairs = []
        for item in value:
            if not isinstance(item, dict):
                return None
            criterion_id = (
                item.get("criterion_id") or item.get("criterion") or item.get("id") or item.get("criterion_key")
            )
            pairs.append((criterion_id, item.get("result")))
    else:
        return None

    result = {}
    for key, item_value in pairs:
        norm_key = clean_str(key, upper=True)
        norm_value = clean_str(item_value, lower=True)
        if norm_key is None or norm_value is None:
            return None
        result[norm_key] = norm_value
    return result


def audit_value(answer, key):
    audit = answer.get("basis_audit")
    if not isinstance(audit, dict):
        return None
    return audit.get(key)


def evaluate(answer):
    expected_criteria = EXPECTED["criteria_results"]
    criteria = normalized_criteria(answer.get("criteria_results"))
    missing = normalized_set(answer.get("missing_information"), lower=True)
    evidence = normalized_list(answer.get("evidence_documents"), upper=True)
    excluded = normalized_list(answer.get("excluded_documents"), upper=True)

    checks = {
        "target_case_and_requested_speech_service": {
            "pass": (
                clean_str(answer.get("case_id"), upper=True) == EXPECTED["case_id"]
                and clean_str(answer.get("requested_cpt")) == EXPECTED["requested_cpt"]
                and clean_str(answer.get("modifier"), upper=True) == EXPECTED["modifier"]
                and as_int(answer.get("requested_units")) == EXPECTED["requested_units"]
            ),
            "details": {
                "expected_case_id": EXPECTED["case_id"],
                "expected_requested_cpt": EXPECTED["requested_cpt"],
                "expected_modifier": EXPECTED["modifier"],
                "expected_requested_units": EXPECTED["requested_units"],
            },
        },
        "pend_disposition_and_route": {
            "pass": (
                clean_str(answer.get("recommendation"), lower=True) == EXPECTED["recommendation"]
                and clean_str(answer.get("final_status"), lower=True) == EXPECTED["final_status"]
                and clean_str(answer.get("route"), lower=True) == EXPECTED["route"]
            ),
            "details": {
                "expected_recommendation": EXPECTED["recommendation"],
                "expected_final_status": EXPECTED["final_status"],
                "expected_route": EXPECTED["route"],
            },
        },
        "speech_therapy_criteria_results": {
            "pass": criteria == expected_criteria,
            "details": {
                "expected_criteria_results": expected_criteria,
            },
        },
        "missing_information_set": {
            "pass": missing == EXPECTED["missing_information"],
            "details": {
                "expected_missing_information": sorted(EXPECTED["missing_information"]),
            },
        },
        "current_evidence_and_stale_exclusion": {
            "pass": (evidence == EXPECTED["evidence_documents"] and excluded == EXPECTED["excluded_documents"]),
            "details": {
                "expected_evidence_documents": EXPECTED["evidence_documents"],
                "expected_excluded_documents": EXPECTED["excluded_documents"],
            },
        },
        "approved_units_and_due_date": {
            "pass": (
                as_int(answer.get("approved_units")) == EXPECTED["approved_units"]
                and clean_str(answer.get("due_date")) == EXPECTED["due_date"]
            ),
            "details": {
                "expected_approved_units": EXPECTED["approved_units"],
                "expected_due_date": EXPECTED["due_date"],
            },
        },
        "basis_source_precedence": {
            "pass": (
                clean_str(audit_value(answer, "source_precedence"), lower=True)
                == EXPECTED["basis_audit"]["source_precedence"]
            ),
            "details": {
                "expected_source_precedence": EXPECTED["basis_audit"]["source_precedence"],
            },
        },
        "basis_controlling_records": {
            "pass": (
                normalized_list(audit_value(answer, "controlling_record_ids"), lower=True)
                == EXPECTED["basis_audit"]["controlling_record_ids"]
            ),
            "details": {
                "expected_controlling_record_ids": EXPECTED["basis_audit"]["controlling_record_ids"],
            },
        },
        "basis_precedence_record_order": {
            "pass": (
                normalized_list(audit_value(answer, "precedence_record_order"), lower=True)
                == EXPECTED["basis_audit"]["precedence_record_order"]
            ),
            "details": {
                "expected_precedence_record_order": EXPECTED["basis_audit"]["precedence_record_order"],
            },
        },
        "basis_exception_records": {
            "pass": (
                normalized_list(audit_value(answer, "exception_record_ids"), lower=True)
                == EXPECTED["basis_audit"]["exception_record_ids"]
            ),
            "details": {
                "expected_exception_record_ids": EXPECTED["basis_audit"]["exception_record_ids"],
            },
        },
    }

    total_weight = sum(weight for _, weight, _ in RUBRIC)
    points = []
    earned_weight = 0
    for name, weight, goal in RUBRIC:
        passed = bool(checks[name]["pass"])
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
                "earned_score": assigned_score if passed else 0,
                "details": checks[name]["details"],
            }
        )

    return {
        "score": earned_weight / total_weight,
        "points": points,
        "total_weight": total_weight,
    }


def main():
    answer_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    try:
        with answer_path.open("r", encoding="utf-8") as f:
            answer = json.load(f)
    except Exception as exc:
        total_weight = sum(weight for _, weight, _ in RUBRIC)
        result = {
            "score": 0,
            "points": [
                {
                    "name": name,
                    "goal": goal,
                    "weight": weight,
                    "assigned_score": weight / total_weight,
                    "passed": False,
                    "earned_score": 0,
                    "details": {"error": f"Could not load submitted JSON: {exc}"},
                }
                for name, weight, goal in RUBRIC
            ],
            "total_weight": total_weight,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    if not isinstance(answer, dict):
        answer = {}
    print(json.dumps(evaluate(answer), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
