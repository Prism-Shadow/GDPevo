#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "batch_id": "train_intake_batch",
    "cases": [
        {
            "case_id": "AUTH00001",
            "first_failing_check": "duplicate_authorization",
            "intake_disposition": "duplicate_halt",
            "duplicate_existing_auth_ids": ["EXA00001"],
            "gold_card_decision": "not_reached_intake_halt",
            "review_queue": "No Review - Intake Halt",
            "urgency_class": "routine",
            "sla_due_at": "2025-02-06T08:00",
            "sla_basis": "CA Commercial calendar 5 days",
            "provider_item": "none",
            "notice_required": True,
        },
        {
            "case_id": "AUTH00002",
            "first_failing_check": "duplicate_authorization",
            "intake_disposition": "duplicate_halt",
            "duplicate_existing_auth_ids": ["EXA00002"],
            "gold_card_decision": "not_reached_intake_halt",
            "review_queue": "No Review - Intake Halt",
            "urgency_class": "routine",
            "sla_due_at": "2025-02-05T09:07",
            "sla_basis": "NY Commercial business 3 days",
            "provider_item": "none",
            "notice_required": True,
        },
        {
            "case_id": "AUTH00003",
            "first_failing_check": "cob_completion",
            "intake_disposition": "cob_hold",
            "duplicate_existing_auth_ids": [],
            "gold_card_decision": "not_reached_intake_halt",
            "review_queue": "No Review - Intake Halt",
            "urgency_class": "routine",
            "sla_due_at": "2025-02-10T10:14",
            "sla_basis": "FL Medicare Advantage calendar 7 days",
            "provider_item": "none",
            "notice_required": False,
        },
        {
            "case_id": "AUTH00004",
            "first_failing_check": "retrospective_submission",
            "intake_disposition": "retrospective_submission_halt",
            "duplicate_existing_auth_ids": [],
            "gold_card_decision": "not_reached_intake_halt",
            "review_queue": "No Review - Intake Halt",
            "urgency_class": "routine",
            "sla_due_at": "2025-02-11T11:21",
            "sla_basis": "PA/FL Medicare Advantage calendar 7 days",
            "provider_item": "requesting_provider_active_sanction",
            "notice_required": True,
        },
        {
            "case_id": "AUTH00005",
            "first_failing_check": "covered_service",
            "intake_disposition": "noncovered_service_denial",
            "duplicate_existing_auth_ids": [],
            "gold_card_decision": "not_reached_intake_halt",
            "review_queue": "No Review - Intake Halt",
            "urgency_class": "routine",
            "sla_due_at": "2025-02-09T12:28",
            "sla_basis": "TX Medicaid calendar 4 days",
            "provider_item": "none",
            "notice_required": True,
        },
        {
            "case_id": "AUTH00006",
            "first_failing_check": "duplicate_authorization",
            "intake_disposition": "duplicate_halt",
            "duplicate_existing_auth_ids": ["EXA00006"],
            "gold_card_decision": "not_reached_intake_halt",
            "review_queue": "No Review - Intake Halt",
            "urgency_class": "routine",
            "sla_due_at": "2025-02-11T13:35",
            "sla_basis": "IL Exchange calendar 5 days",
            "provider_item": "none",
            "notice_required": True,
        },
    ],
    "sla_summary": {
        "routine_count": 6,
        "urgent_count": 0,
        "stat_count": 0,
        "notice_required_count": 5,
        "ready_for_clinical_review_count": 0,
        "auto_approved_count": 0,
        "duplicate_halt_count": 3,
    },
}


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(json.dumps({"score": 0, "max_score": 1, "error": f"invalid_json: {exc}", "points": []}))
        sys.exit(0)


def normalize_cases(data):
    cases = data.get("cases", [])
    if not isinstance(cases, list):
        return {}
    normalized = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = case.get("case_id")
        if isinstance(case_id, str):
            item = dict(case)
            refs = item.get("duplicate_existing_auth_ids", [])
            item["duplicate_existing_auth_ids"] = sorted(refs) if isinstance(refs, list) else refs
            normalized[case_id] = item
    return normalized


def case_fields_match(actual_cases, expected_cases, fields):
    for expected in expected_cases:
        actual = actual_cases.get(expected["case_id"])
        if not isinstance(actual, dict):
            return False
        for field in fields:
            if actual.get(field) != expected.get(field):
                return False
    return True


def summary_match(actual, expected, fields):
    summary = actual.get("sla_summary")
    if not isinstance(summary, dict):
        return False
    return all(summary.get(field) == expected["sla_summary"][field] for field in fields)


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {"score": 0, "max_score": 1, "error": "usage: evaluator.py /path/to/prediction.json", "points": []}
            )
        )
        return

    actual = load_json(Path(sys.argv[1]))
    actual_cases = normalize_cases(actual)
    expected_cases = EXPECTED["cases"]

    checks = [
        {
            "id": "SP001_case_first_failing_dispositions",
            "weight": 3,
            "ok": actual.get("batch_id") == EXPECTED["batch_id"]
            and case_fields_match(actual_cases, expected_cases, ["first_failing_check", "intake_disposition"]),
        },
        {
            "id": "SP002_gold_card_and_clinical_review_decisions",
            "weight": 2,
            "ok": case_fields_match(actual_cases, expected_cases, ["gold_card_decision"])
            and summary_match(actual, EXPECTED, ["ready_for_clinical_review_count", "auto_approved_count"]),
        },
        {
            "id": "SP003_urgency_and_sla_due",
            "weight": 2,
            "ok": case_fields_match(actual_cases, expected_cases, ["urgency_class", "sla_due_at", "sla_basis"])
            and summary_match(actual, EXPECTED, ["routine_count", "urgent_count", "stat_count"]),
        },
        {
            "id": "SP004_review_queue_or_disposition",
            "weight": 2,
            "ok": case_fields_match(actual_cases, expected_cases, ["review_queue"]),
        },
        {
            "id": "SP005_duplicate_handling",
            "weight": 2,
            "ok": case_fields_match(actual_cases, expected_cases, ["duplicate_existing_auth_ids"])
            and summary_match(actual, EXPECTED, ["duplicate_halt_count"]),
        },
        {
            "id": "SP006_provider_item",
            "weight": 1,
            "ok": case_fields_match(actual_cases, expected_cases, ["provider_item"]),
        },
        {
            "id": "SP007_notice_count",
            "weight": 1,
            "ok": case_fields_match(actual_cases, expected_cases, ["notice_required"])
            and summary_match(actual, EXPECTED, ["notice_required_count"]),
        },
    ]

    raw_max = sum(check["weight"] for check in checks)
    raw_score = sum(check["weight"] for check in checks if check["ok"])
    points = [
        {
            "id": check["id"],
            "weight": check["weight"],
            "earned": check["weight"] if check["ok"] else 0,
            "passed": check["ok"],
        }
        for check in checks
    ]
    print(
        json.dumps(
            {
                "score": raw_score / raw_max,
                "max_score": 1.0,
                "raw_score": raw_score,
                "raw_max": raw_max,
                "points": points,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
