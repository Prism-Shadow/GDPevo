#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PATIENT_IDS = ["P007", "P008", "P009", "P010", "P011", "P012", "P013"]

GOLD: dict[str, Any] = {
    "task_id": "test_001",
    "roster_id": "NPI-JUL-02",
    "requested_service_date": "2026-07-09",
    "service_line": "primary_care",
    "patient_results": [
        {
            "patient_id": "P007",
            "insurance_status": "invalid",
            "prescription_status": "valid",
            "pharmacy_status": "in_network",
            "lifestyle_risk": "medium",
            "overall_risk": "high",
            "registration_status": "rejected",
            "blocked_reason_codes": ["coverage_out_of_network", "overall_risk_high"],
        },
        {
            "patient_id": "P008",
            "insurance_status": "invalid",
            "prescription_status": "valid",
            "pharmacy_status": "out_of_network",
            "lifestyle_risk": "medium",
            "overall_risk": "medium",
            "registration_status": "rejected",
            "blocked_reason_codes": ["coverage_expired", "pharmacy_out_of_network"],
        },
        {
            "patient_id": "P009",
            "insurance_status": "valid",
            "prescription_status": "invalid",
            "pharmacy_status": "in_network",
            "lifestyle_risk": "low",
            "overall_risk": "medium",
            "registration_status": "hold",
            "blocked_reason_codes": ["pbm_invalid"],
        },
        {
            "patient_id": "P010",
            "insurance_status": "valid",
            "prescription_status": "invalid",
            "pharmacy_status": "in_network",
            "lifestyle_risk": "high",
            "overall_risk": "high",
            "registration_status": "clinical_review",
            "blocked_reason_codes": ["pbm_invalid", "overall_risk_high"],
        },
        {
            "patient_id": "P011",
            "insurance_status": "invalid",
            "prescription_status": "valid",
            "pharmacy_status": "out_of_network",
            "lifestyle_risk": "low",
            "overall_risk": "high",
            "registration_status": "rejected",
            "blocked_reason_codes": [
                "coverage_expired",
                "pharmacy_out_of_network",
                "preferred_contact_unavailable",
                "overall_risk_high",
            ],
        },
        {
            "patient_id": "P012",
            "insurance_status": "invalid",
            "prescription_status": "valid",
            "pharmacy_status": "in_network",
            "lifestyle_risk": "high",
            "overall_risk": "high",
            "registration_status": "rejected",
            "blocked_reason_codes": ["coverage_pending", "excluded_service_line", "overall_risk_high"],
        },
        {
            "patient_id": "P013",
            "insurance_status": "invalid",
            "prescription_status": "invalid",
            "pharmacy_status": "out_of_network",
            "lifestyle_risk": "high",
            "overall_risk": "high",
            "registration_status": "rejected",
            "blocked_reason_codes": [
                "excluded_service_line",
                "pbm_policy_mismatch",
                "pharmacy_out_of_network",
                "missing_address",
                "overall_risk_high",
            ],
        },
    ],
    "cohort_summary": {
        "total_patients": 7,
        "counts_by_registration_status": {"approved": 0, "hold": 1, "clinical_review": 1, "rejected": 5},
        "counts_by_overall_risk": {"low": 0, "medium": 2, "high": 5},
        "counts_by_lifestyle_risk": {"low": 2, "medium": 2, "high": 3},
    },
}

RUBRIC = [
    ("SP001", "Correct primary insurance status for all target patients.", 2),
    ("SP002", "Correct prescription benefit status for all target patients.", 2),
    ("SP003", "Correct preferred-pharmacy network status for all target patients.", 2),
    ("SP004", "Correct lifestyle risk classification for all target patients.", 2),
    ("SP005", "Correct overall risk classification for all target patients.", 2),
    ("SP006", "Correct final registration status for all target patients.", 3),
    ("SP007", "Correct blocked reason-code set for every target patient.", 3),
    ("SP008", "Correct cohort summary counts by final status and risk.", 1),
]


def load_answer(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:  # noqa: BLE001
        return None, f"failed to parse JSON: {exc}"
    if not isinstance(data, dict):
        return None, "answer must be a JSON object"
    return data, None


def patient_map(answer: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(answer, dict):
        return {}
    rows = answer.get("patient_results")
    if isinstance(rows, dict):
        rows = [dict(value, patient_id=key) if isinstance(value, dict) else value for key, value in rows.items()]
    if not isinstance(rows, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for item in rows:
        if isinstance(item, dict) and isinstance(item.get("patient_id"), str):
            mapped[item["patient_id"]] = item
    return mapped


def gold_patient_map() -> dict[str, dict[str, Any]]:
    return {row["patient_id"]: row for row in GOLD["patient_results"]}


def compare_field(answer: dict[str, Any] | None, field: str) -> tuple[bool, dict[str, Any]]:
    got_rows = patient_map(answer)
    gold_rows = gold_patient_map()
    expected = {pid: gold_rows[pid][field] for pid in PATIENT_IDS}
    got = {pid: got_rows.get(pid, {}).get(field) for pid in PATIENT_IDS}
    return got == expected, {"expected": expected, "got": got}


def normalize_reason_codes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item).strip() for item in value if isinstance(item, str) and str(item).strip())


def compare_reasons(answer: dict[str, Any] | None) -> tuple[bool, dict[str, Any]]:
    got_rows = patient_map(answer)
    gold_rows = gold_patient_map()
    expected = {pid: normalize_reason_codes(gold_rows[pid]["blocked_reason_codes"]) for pid in PATIENT_IDS}
    got = {pid: normalize_reason_codes(got_rows.get(pid, {}).get("blocked_reason_codes")) for pid in PATIENT_IDS}
    return got == expected, {"expected": expected, "got": got}


def normalize_counts(summary: Any, key: str, labels: list[str]) -> dict[str, int | None]:
    if not isinstance(summary, dict):
        return dict.fromkeys(labels)
    raw = summary.get(key)
    if not isinstance(raw, dict):
        return dict.fromkeys(labels)
    normalized: dict[str, int | None] = {}
    for label in labels:
        value = raw.get(label, 0)
        normalized[label] = value if isinstance(value, int) and not isinstance(value, bool) else None
    return normalized


def compare_summary(answer: dict[str, Any] | None) -> tuple[bool, dict[str, Any]]:
    got_summary = answer.get("cohort_summary") if isinstance(answer, dict) else None
    gold_summary = GOLD["cohort_summary"]
    expected = {
        "total_patients": gold_summary["total_patients"],
        "counts_by_registration_status": gold_summary["counts_by_registration_status"],
        "counts_by_overall_risk": gold_summary["counts_by_overall_risk"],
        "counts_by_lifestyle_risk": gold_summary["counts_by_lifestyle_risk"],
    }
    got = {
        "total_patients": got_summary.get("total_patients") if isinstance(got_summary, dict) else None,
        "counts_by_registration_status": normalize_counts(
            got_summary,
            "counts_by_registration_status",
            ["approved", "hold", "clinical_review", "rejected"],
        ),
        "counts_by_overall_risk": normalize_counts(got_summary, "counts_by_overall_risk", ["low", "medium", "high"]),
        "counts_by_lifestyle_risk": normalize_counts(
            got_summary, "counts_by_lifestyle_risk", ["low", "medium", "high"]
        ),
    }
    return got == expected, {"expected": expected, "got": got}


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    answer, parse_error = load_answer(path)
    total_weight = sum(weight for _, _, weight in RUBRIC)
    checks = {
        "SP001": lambda: compare_field(answer, "insurance_status"),
        "SP002": lambda: compare_field(answer, "prescription_status"),
        "SP003": lambda: compare_field(answer, "pharmacy_status"),
        "SP004": lambda: compare_field(answer, "lifestyle_risk"),
        "SP005": lambda: compare_field(answer, "overall_risk"),
        "SP006": lambda: compare_field(answer, "registration_status"),
        "SP007": lambda: compare_reasons(answer),
        "SP008": lambda: compare_summary(answer),
    }

    points = []
    score = 0.0
    for point_id, goal, raw_weight in RUBRIC:
        assigned = raw_weight / total_weight
        if parse_error:
            passed = False
            details = {"error": parse_error}
        else:
            passed, details = checks[point_id]()
        earned = assigned if passed else 0.0
        score += earned
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": raw_weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
                "details": details,
            }
        )

    result = {
        "score": round(score, 10),
        "correct": score == 1.0,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
