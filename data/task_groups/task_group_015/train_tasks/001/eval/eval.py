#!/usr/bin/env python3
"""Evaluator for train_001 duplicate merge readiness.

Rubric: ten whole-point checks cover merge decision, active clinical-list
preservation, identity signals, document evidence, audit evidence, distractor
exclusion, readiness, and packet contact. Each check is pass/fail; raw weights
are 1, 2, or 3 only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED = {
    "candidate_id": "DUP-TR-001",
    "target_patient_id": "P-31014",
    "source_patient_id": "P-88420",
    "disposition": "ready_to_merge",
    "merge_decision": {
        "disposition": "merge_ready",
        "canonical_target_patient_id": "P-31014",
        "source_patient_id": "P-88420",
        "manual_review_required": False,
        "reason_codes": {
            "active_duplicate_candidate",
            "duplicate_record_already_points_to_target",
            "strong_identity_match",
        },
    },
    "active_condition_keys": {
        "copd",
        "coronary_artery_disease",
        "diabetes_type_2",
        "hypertension",
        "right_knee_oa",
    },
    "active_medication_keys": {"aspirin", "baseline_med", "metformin"},
    "active_allergy_keys": {"baseline_allergy", "iodinated_contrast", "penicillin"},
    "match_signals": {
        "name_variant",
        "same_dob",
        "same_insurance",
        "same_phone",
        "shared_external_cardiology_document",
    },
    "conflict_signals": {"address_abbreviation"},
    "document_ids": {"DOC-CARD-TR-001", "DOC-MERGE-TR-001-A"},
    "audit_ids": {"AUD-TR-001-A", "AUD-TR-001-B"},
    "excluded_distractors": {
        "condition_keys": {"left_knee_oa"},
        "medication_keys": {"naproxen"},
        "document_ids": {"DOC-2B6141CA", "DOC-E1547158"},
        "audit_ids": set(),
    },
    "active_list_reconciliation": {
        "authoritative_source": "patient_active_list_endpoints_over_duplicate_preview",
        "condition_keys_added_from_active_endpoints": {"copd", "right_knee_oa"},
        "medication_keys_added_from_active_endpoints": {"baseline_med"},
        "allergy_keys_added_from_active_endpoints": {"baseline_allergy"},
    },
    "document_selection_policy": {
        "packet_document_basis": "identity_or_external_continuity_documents_only",
        "excluded_document_types": {"chart_summary"},
    },
    "packet_readiness": {
        "ready_for_merge_packet": True,
        "readiness_status": "ready",
        "required_review_notes": set(),
    },
    "specialist_provider": {
        "provider_id": "PRV-CARD-020",
        "name": "Dr. Renee Okafor",
        "facility": "Summit Heart Center",
        "phone": "555-430-2020",
        "fax": "555-430-2299",
    },
}

POINTS = [
    {
        "id": "source_target_disposition",
        "weight": 3,
        "comment": "Candidate, canonical target/source, and merge disposition are correct.",
    },
    {
        "id": "merge_decision_packet_fields",
        "weight": 2,
        "comment": "Test-family merge decision fields and packet readiness are correct.",
    },
    {
        "id": "condition_union",
        "weight": 2,
        "comment": "Active condition normalized-key union is exact.",
    },
    {
        "id": "medication_union",
        "weight": 2,
        "comment": "Active medication normalized-key union is exact.",
    },
    {
        "id": "allergy_union",
        "weight": 2,
        "comment": "Active allergy normalized-key union is exact.",
    },
    {
        "id": "match_conflict_signals",
        "weight": 2,
        "comment": "Duplicate match and conflict signal sets are exact.",
    },
    {
        "id": "document_evidence",
        "weight": 2,
        "comment": "Relevant document evidence IDs are exact.",
    },
    {
        "id": "audit_evidence",
        "weight": 2,
        "comment": "Relevant audit evidence IDs are exact.",
    },
    {
        "id": "excluded_distractors",
        "weight": 2,
        "comment": "Inactive clinical and unrelated document distractors are excluded.",
    },
    {
        "id": "specialist_provider_contact",
        "weight": 1,
        "comment": "Specialist contact for the packet identifies the cardiology provider and contact details.",
    },
]


def norm_scalar(value: Any) -> str:
    return str(value).strip()


def norm_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {norm_scalar(item) for item in value if norm_scalar(item)}
    if isinstance(value, set):
        return {norm_scalar(item) for item in value if norm_scalar(item)}
    if isinstance(value, str):
        return {norm_scalar(value)} if norm_scalar(value) else set()
    return set()


def get_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def values_for_key(obj: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(obj, dict):
        for k, value in obj.items():
            if k == key:
                found.append(value)
            found.extend(values_for_key(value, key))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(values_for_key(item, key))
    return found


def first_value(obj: Any, paths: list[str], key: str | None = None) -> Any:
    for path in paths:
        value = get_path(obj, path)
        if value is not None:
            return value
    if key:
        values = values_for_key(obj, key)
        if values:
            return values[0]
    return None


def set_value(obj: Any, paths: list[str], key: str) -> set[str]:
    value = first_value(obj, paths, key)
    return norm_set(value)


def contact_pass(answer: Any) -> bool:
    contact = get_path(answer, "packet_contact.specialist_provider")
    if not isinstance(contact, dict):
        contact = {}
    blob = json.dumps(contact if contact else answer, sort_keys=True)
    return all(expected in blob for expected in EXPECTED["specialist_provider"].values())


def merge_decision_packet_pass(answer: Any) -> bool:
    md = get_path(answer, "merge_decision")
    pr = get_path(answer, "packet_readiness")
    if not isinstance(md, dict) or not isinstance(pr, dict):
        return False
    expected_md = EXPECTED["merge_decision"]
    expected_pr = EXPECTED["packet_readiness"]
    return (
        md.get("disposition") == expected_md["disposition"]
        and md.get("canonical_target_patient_id") == expected_md["canonical_target_patient_id"]
        and md.get("source_patient_id") == expected_md["source_patient_id"]
        and md.get("manual_review_required") is expected_md["manual_review_required"]
        and norm_set(md.get("reason_codes")) == expected_md["reason_codes"]
        and pr.get("ready_for_merge_packet") is expected_pr["ready_for_merge_packet"]
        and pr.get("readiness_status") == expected_pr["readiness_status"]
        and norm_set(pr.get("required_review_notes")) == expected_pr["required_review_notes"]
    )


def excluded_distractors_pass(answer: Any) -> bool:
    excluded = get_path(answer, "excluded_distractors")
    if not isinstance(excluded, dict):
        return False
    expected = EXPECTED["excluded_distractors"]
    reconciliation = get_path(answer, "active_list_reconciliation")
    if not isinstance(reconciliation, dict):
        reconciliation = {}
    expected_reconciliation = EXPECTED["active_list_reconciliation"]
    document_policy = get_path(answer, "document_selection_policy")
    if not isinstance(document_policy, dict):
        document_policy = {}
    expected_document_policy = EXPECTED["document_selection_policy"]
    return (
        norm_set(excluded.get("condition_keys")) == expected["condition_keys"]
        and norm_set(excluded.get("medication_keys")) == expected["medication_keys"]
        and norm_set(excluded.get("document_ids")) == expected["document_ids"]
        and norm_set(excluded.get("audit_ids")) == expected["audit_ids"]
        and reconciliation.get("authoritative_source") == expected_reconciliation["authoritative_source"]
        and norm_set(reconciliation.get("condition_keys_added_from_active_endpoints"))
        == expected_reconciliation["condition_keys_added_from_active_endpoints"]
        and norm_set(reconciliation.get("medication_keys_added_from_active_endpoints"))
        == expected_reconciliation["medication_keys_added_from_active_endpoints"]
        and norm_set(reconciliation.get("allergy_keys_added_from_active_endpoints"))
        == expected_reconciliation["allergy_keys_added_from_active_endpoints"]
        and document_policy.get("packet_document_basis") == expected_document_policy["packet_document_basis"]
        and norm_set(document_policy.get("excluded_document_types"))
        == expected_document_policy["excluded_document_types"]
    )


def evaluate(answer: Any) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    candidate_id = norm_scalar(first_value(answer, ["candidate_id"], "candidate_id"))
    target_id = norm_scalar(first_value(answer, ["merge.target_patient_id", "target_patient_id"], "target_patient_id"))
    source_id = norm_scalar(first_value(answer, ["merge.source_patient_id", "source_patient_id"], "source_patient_id"))
    disposition = norm_scalar(first_value(answer, ["merge.disposition", "disposition"], "disposition"))
    checks["source_target_disposition"] = (
        candidate_id == EXPECTED["candidate_id"]
        and target_id == EXPECTED["target_patient_id"]
        and source_id == EXPECTED["source_patient_id"]
        and disposition == EXPECTED["disposition"]
    )
    checks["merge_decision_packet_fields"] = merge_decision_packet_pass(answer)

    checks["condition_union"] = (
        set_value(answer, ["clinical_unions.active_condition_keys"], "active_condition_keys")
        == EXPECTED["active_condition_keys"]
    )
    checks["medication_union"] = (
        set_value(answer, ["clinical_unions.active_medication_keys"], "active_medication_keys")
        == EXPECTED["active_medication_keys"]
    )
    checks["allergy_union"] = (
        set_value(answer, ["clinical_unions.active_allergy_keys"], "active_allergy_keys")
        == EXPECTED["active_allergy_keys"]
    )
    checks["match_conflict_signals"] = (
        set_value(answer, ["identity_signals.match_signals"], "match_signals") == EXPECTED["match_signals"]
        and set_value(answer, ["identity_signals.conflict_signals"], "conflict_signals")
        == EXPECTED["conflict_signals"]
    )
    checks["document_evidence"] = (
        set_value(answer, ["evidence.document_ids"], "document_ids") == EXPECTED["document_ids"]
    )
    checks["audit_evidence"] = set_value(answer, ["evidence.audit_ids"], "audit_ids") == EXPECTED["audit_ids"]
    checks["excluded_distractors"] = excluded_distractors_pass(answer)
    checks["specialist_provider_contact"] = contact_pass(answer)

    total_weight = sum(point["weight"] for point in POINTS)
    details = []
    earned_total = 0.0
    for point in POINTS:
        assigned = point["weight"] / total_weight
        passed = bool(checks[point["id"]])
        earned = assigned if passed else 0.0
        earned_total += earned
        details.append(
            {
                "id": point["id"],
                "weight": point["weight"],
                "assigned_score": round(assigned, 6),
                "passed": passed,
                "earned_score": round(earned, 6),
                "comment": point["comment"],
            }
        )

    return {"score": round(earned_total, 6), "points": details}


def main() -> int:
    if len(sys.argv) > 2:
        print(json.dumps({"score": 0.0, "error": "usage: eval.py [candidate_answer.json]"}, indent=2))
        return 2
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            answer = json.load(handle)
    except Exception as exc:  # noqa: BLE001 - evaluator should report JSON for any load failure.
        print(json.dumps({"score": 0.0, "error": f"could not load candidate answer: {exc}", "points": []}, indent=2))
        return 0
    print(json.dumps(evaluate(answer), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
