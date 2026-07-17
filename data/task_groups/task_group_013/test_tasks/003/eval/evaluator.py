#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


GOLD: dict[str, Any] = {
    "batch_id": "DIAL-SUMMER-02",
    "patients": [
        {
            "transfer_id": "TR0007",
            "patient_id": "P020",
            "packet_completeness_status": "incomplete",
            "missing_required_documents": ["hbsag", "pneumonia_vaccine"],
            "stale_documents": [
                {"doc_type": "hep_b_antibody_core", "received_date": "2025-06-02", "freshness_limit_days": 365},
                {"doc_type": "monthly_labs", "received_date": "2025-09-11", "freshness_limit_days": 30},
                {"doc_type": "ppd_or_cxr", "received_date": "2026-03-23", "freshness_limit_days": 30},
            ],
            "requested_start": {
                "date": "2026-07-14",
                "capacity_status": "unavailable",
                "open_chairs_total": 0,
                "feasibility": "packet_not_ready_capacity_unavailable",
            },
            "final_intake_decision": "clinical_review",
            "next_contact_owner": "clinical_nurse",
            "next_contact_route": "fax_referring_facility",
        },
        {
            "transfer_id": "TR0008",
            "patient_id": "P021",
            "packet_completeness_status": "incomplete",
            "missing_required_documents": ["allergy_list"],
            "stale_documents": [
                {"doc_type": "hbsag", "received_date": "2026-05-12", "freshness_limit_days": 30},
                {"doc_type": "monthly_labs", "received_date": "2026-05-12", "freshness_limit_days": 30},
                {"doc_type": "ppd_or_cxr", "received_date": "2026-05-12", "freshness_limit_days": 30},
            ],
            "requested_start": {
                "date": "2026-07-16",
                "capacity_status": "unavailable",
                "open_chairs_total": 0,
                "feasibility": "packet_not_ready_capacity_unavailable",
            },
            "final_intake_decision": "clinical_review",
            "next_contact_owner": "clinical_nurse",
            "next_contact_route": "fax_referring_facility",
        },
        {
            "transfer_id": "TR0009",
            "patient_id": "P022",
            "packet_completeness_status": "incomplete",
            "missing_required_documents": ["flu_vaccine", "hep_b_antibody_core", "pneumonia_vaccine"],
            "stale_documents": [
                {"doc_type": "hbsag", "received_date": "2025-10-22", "freshness_limit_days": 30},
                {"doc_type": "history_physical", "received_date": "2025-07-03", "freshness_limit_days": 365},
                {"doc_type": "monthly_labs", "received_date": "2025-09-07", "freshness_limit_days": 30},
                {"doc_type": "ppd_or_cxr", "received_date": "2026-01-30", "freshness_limit_days": 30},
            ],
            "requested_start": {
                "date": "2026-07-18",
                "capacity_status": "unavailable",
                "open_chairs_total": 0,
                "feasibility": "packet_not_ready_capacity_unavailable",
            },
            "final_intake_decision": "clinical_review",
            "next_contact_owner": "clinical_nurse",
            "next_contact_route": "fax_referring_facility",
        },
        {
            "transfer_id": "TR0010",
            "patient_id": "P023",
            "packet_completeness_status": "incomplete",
            "missing_required_documents": [
                "physician_orders",
                "transportation",
                "treatment_flowsheets",
                "vascular_access_report",
            ],
            "stale_documents": [
                {"doc_type": "ppd_or_cxr", "received_date": "2025-08-20", "freshness_limit_days": 30},
            ],
            "requested_start": {
                "date": "2026-07-20",
                "capacity_status": "available",
                "open_chairs_total": 7,
                "feasibility": "packet_not_ready_capacity_available",
            },
            "final_intake_decision": "clinical_review",
            "next_contact_owner": "clinical_nurse",
            "next_contact_route": "fax_referring_facility",
        },
        {
            "transfer_id": "TR0011",
            "patient_id": "P024",
            "packet_completeness_status": "incomplete",
            "missing_required_documents": ["face_sheet", "vascular_access_report"],
            "stale_documents": [
                {"doc_type": "hbsag", "received_date": "2026-03-23", "freshness_limit_days": 30},
                {"doc_type": "history_physical", "received_date": "2025-06-26", "freshness_limit_days": 365},
                {"doc_type": "monthly_labs", "received_date": "2026-03-12", "freshness_limit_days": 30},
                {"doc_type": "ppd_or_cxr", "received_date": "2026-06-04", "freshness_limit_days": 30},
            ],
            "requested_start": {
                "date": "2026-07-22",
                "capacity_status": "unavailable",
                "open_chairs_total": 0,
                "feasibility": "packet_not_ready_capacity_unavailable",
            },
            "final_intake_decision": "clinical_review",
            "next_contact_owner": "clinical_nurse",
            "next_contact_route": "fax_referring_facility",
        },
        {
            "transfer_id": "TR0012",
            "patient_id": "P025",
            "packet_completeness_status": "incomplete",
            "missing_required_documents": ["hbsag", "treatment_flowsheets"],
            "stale_documents": [
                {"doc_type": "monthly_labs", "received_date": "2025-12-16", "freshness_limit_days": 30},
                {"doc_type": "ppd_or_cxr", "received_date": "2026-03-02", "freshness_limit_days": 30},
            ],
            "requested_start": {
                "date": "2026-07-24",
                "capacity_status": "available",
                "open_chairs_total": 7,
                "feasibility": "packet_not_ready_capacity_available",
            },
            "final_intake_decision": "clinical_review",
            "next_contact_owner": "clinical_nurse",
            "next_contact_route": "fax_referring_facility",
        },
    ],
    "cohort_summary": {
        "total_transfers": 6,
        "complete_documents_count": 0,
        "missing_document_patient_count": 6,
        "stale_document_patient_count": 6,
        "capacity_available_count": 2,
        "requested_start_ready_count": 0,
        "decision_counts": {"accept": 0, "hold": 0, "clinical_review": 6},
        "next_contact_owner_counts": {
            "clinical_nurse": 6,
            "intake_coordinator": 0,
            "scheduling_coordinator": 0,
            "none": 0,
        },
    },
}

RUBRIC = [
    ("SP001", "Correct packet completeness status for all transfer patients.", 3),
    ("SP002", "Correct stale-document detection for freshness-limited packet items.", 3),
    ("SP003", "Correct missing required-document sets for all transfer patients.", 2),
    ("SP004", "Correct requested-start feasibility using packet readiness and chair capacity.", 2),
    ("SP005", "Correct final intake decision for each transfer patient.", 3),
    ("SP006", "Correct next-contact owner and route for each non-accepted patient.", 2),
    ("SP007", "Correct cohort summary counts.", 1),
]


def load_answer(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001 - evaluator reports parse failures as JSON.
        return None, f"Could not parse JSON: {exc}"
    if not isinstance(data, dict):
        return None, "Top-level answer must be a JSON object."
    return data, None


def patient_map(answer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = answer.get("patients")
    if not isinstance(records, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, dict) and isinstance(record.get("transfer_id"), str):
            mapped[record["transfer_id"]] = record
    return mapped


def as_doc_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    docs: set[str] = set()
    for item in value:
        if isinstance(item, str):
            docs.add(item.strip())
        elif isinstance(item, dict) and isinstance(item.get("doc_type"), str):
            docs.add(item["doc_type"].strip())
    return docs


def stale_signature(value: Any) -> set[tuple[str, str, int]]:
    if not isinstance(value, list):
        return set()
    sig: set[tuple[str, str, int]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        doc_type = item.get("doc_type")
        received = item.get("received_date")
        limit = item.get("freshness_limit_days")
        try:
            limit_int = int(limit)
        except (TypeError, ValueError):
            continue
        if isinstance(doc_type, str) and isinstance(received, str):
            sig.add((doc_type.strip(), received.strip(), limit_int))
    return sig


def start_tuple(record: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    start = record.get("requested_start")
    if not isinstance(start, dict):
        return (None, None, None, None)
    try:
        chairs = int(start.get("open_chairs_total"))
    except (TypeError, ValueError):
        chairs = None
    return (
        start.get("date"),
        start.get("capacity_status"),
        chairs,
        start.get("feasibility"),
    )


def expected_transfer_ids() -> set[str]:
    return {p["transfer_id"] for p in GOLD["patients"]}


def check_patient_key(answer: dict[str, Any], key: str) -> bool:
    got = patient_map(answer)
    if set(got) != expected_transfer_ids():
        return False
    return all(got[gold["transfer_id"]].get(key) == gold[key] for gold in GOLD["patients"])


def check_stale(answer: dict[str, Any]) -> bool:
    got = patient_map(answer)
    if set(got) != expected_transfer_ids():
        return False
    return all(
        stale_signature(got[gold["transfer_id"]].get("stale_documents")) == stale_signature(gold["stale_documents"])
        for gold in GOLD["patients"]
    )


def check_missing(answer: dict[str, Any]) -> bool:
    got = patient_map(answer)
    if set(got) != expected_transfer_ids():
        return False
    return all(
        as_doc_set(got[gold["transfer_id"]].get("missing_required_documents"))
        == set(gold["missing_required_documents"])
        for gold in GOLD["patients"]
    )


def check_start(answer: dict[str, Any]) -> bool:
    got = patient_map(answer)
    if set(got) != expected_transfer_ids():
        return False
    return all(start_tuple(got[gold["transfer_id"]]) == start_tuple(gold) for gold in GOLD["patients"])


def check_contact(answer: dict[str, Any]) -> bool:
    got = patient_map(answer)
    if set(got) != expected_transfer_ids():
        return False
    for gold in GOLD["patients"]:
        record = got[gold["transfer_id"]]
        if record.get("next_contact_owner") != gold["next_contact_owner"]:
            return False
        if record.get("next_contact_route") != gold["next_contact_route"]:
            return False
    return True


def normalize_summary(summary: Any) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    keys = [
        "total_transfers",
        "complete_documents_count",
        "missing_document_patient_count",
        "stale_document_patient_count",
        "capacity_available_count",
        "requested_start_ready_count",
    ]
    out: dict[str, Any] = {}
    for key in keys:
        try:
            out[key] = int(summary.get(key))
        except (TypeError, ValueError):
            out[key] = None
    for nested in ["decision_counts", "next_contact_owner_counts"]:
        value = summary.get(nested)
        if not isinstance(value, dict):
            out[nested] = {}
            continue
        out[nested] = {}
        for key, count in value.items():
            try:
                out[nested][key] = int(count)
            except (TypeError, ValueError):
                out[nested][key] = None
    return out


def check_summary(answer: dict[str, Any]) -> bool:
    return normalize_summary(answer.get("cohort_summary")) == normalize_summary(GOLD["cohort_summary"])


def evaluate(answer: dict[str, Any] | None, parse_error: str | None) -> dict[str, Any]:
    total_weight = sum(weight for _, _, weight in RUBRIC)
    checks = {point_id: False for point_id, _, _ in RUBRIC}
    details: dict[str, Any] = {"parse_error": parse_error} if parse_error else {}
    if answer is not None:
        checks = {
            "SP001": check_patient_key(answer, "packet_completeness_status"),
            "SP002": check_stale(answer),
            "SP003": check_missing(answer),
            "SP004": check_start(answer),
            "SP005": check_patient_key(answer, "final_intake_decision"),
            "SP006": check_contact(answer),
            "SP007": check_summary(answer),
        }
        details["batch_id_match"] = answer.get("batch_id") == GOLD["batch_id"]
        if not details["batch_id_match"]:
            checks = dict.fromkeys(checks, False)

    points = []
    score = 0.0
    for point_id, goal, weight in RUBRIC:
        assigned = weight / total_weight
        passed = bool(checks[point_id])
        earned = assigned if passed else 0.0
        score += earned
        points.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
            }
        )
    return {
        "score": score,
        "correct": abs(score - 1.0) < 1e-9,
        "points": points,
        "details": details,
    }


def main() -> None:
    answer_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    answer, parse_error = load_answer(answer_path)
    print(json.dumps(evaluate(answer, parse_error), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
