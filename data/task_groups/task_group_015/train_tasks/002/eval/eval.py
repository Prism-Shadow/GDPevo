#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


POINTS: list[dict[str, Any]] = [
    {
        "id": "identity",
        "weight": 2,
        "goal": "Correct patient/referral identity and referral header fields.",
    },
    {
        "id": "clinical_diagnoses",
        "weight": 2,
        "goal": "Correct active diagnosis set and cardiology referral code validation.",
    },
    {
        "id": "allergy_details",
        "weight": 2,
        "goal": "Correct active sulfa allergy details and allergy readiness classification.",
    },
    {
        "id": "recent_encounter",
        "weight": 2,
        "goal": "Correct referral-relevant signed encounter evidence.",
    },
    {
        "id": "echo_document",
        "weight": 2,
        "goal": "Correct final echocardiogram evidence and document packet status.",
    },
    {
        "id": "receiving_provider",
        "weight": 2,
        "goal": "Correct receiving cardiology provider and directory fields.",
    },
    {
        "id": "medication_highlight",
        "weight": 1,
        "goal": "Correct referral-relevant medication highlights.",
    },
    {
        "id": "authorization_readiness",
        "weight": 2,
        "goal": "Correct authorization, blocker, overall readiness, and letter readiness choices.",
    },
]


def norm(value: Any) -> str:
    return str(value).strip().lower()


def get(data: Any, path: str, default: Any = None) -> Any:
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def str_eq(data: Any, path: str, expected: str) -> bool:
    return norm(get(data, path)) == norm(expected)


def bool_eq(data: Any, path: str, expected: bool) -> bool:
    return get(data, path) is expected


def list_of_dicts(data: Any, path: str) -> list[dict[str, Any]]:
    value = get(data, path, [])
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def string_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {norm(v) for v in values}


def diagnosis_map(data: Any) -> dict[str, dict[str, Any]]:
    return {norm(item.get("code")): item for item in list_of_dicts(data, "active_diagnoses")}


def medication_map(data: Any) -> dict[str, dict[str, Any]]:
    return {norm(item.get("medication")): item for item in list_of_dicts(data, "medication_highlights")}


def has_all_strings(data: Any, path: str, expected: set[str]) -> bool:
    return string_set(get(data, path, [])) == {norm(v) for v in expected}


def check_identity(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "patient_id": str_eq(data, "patient_referral.patient_id", "P-20177"),
        "referral_id": str_eq(data, "patient_referral.referral_id", "REF-FEB-CARD-007"),
        "batch_id": str_eq(data, "patient_referral.batch_id", "FEB26-CARD"),
        "service_line": str_eq(data, "patient_referral.service_line", "cardiology"),
        "requested_date": str_eq(data, "patient_referral.requested_date", "2026-02-15"),
    }
    return all(checks.values()), checks


def check_clinical_diagnoses(data: Any) -> tuple[bool, dict[str, Any]]:
    diagnoses = diagnosis_map(data)
    expected_codes = {"e11.9", "i10", "i50.32", "m17.11", "r06.02"}
    relevant = {code for code, item in diagnoses.items() if item.get("referral_relevant") is True}
    checks = {
        "active_code_set": set(diagnoses) == expected_codes,
        "referral_relevant_codes": relevant == {"i50.32", "r06.02"},
        "primary_code": str_eq(data, "referral_code_set.primary_code", "I50.32"),
        "supporting_codes": has_all_strings(data, "referral_code_set.supporting_codes", {"R06.02"}),
        "icd_validation": str_eq(data, "referral_code_set.icd_validation", "valid_matches_narrative"),
        "primary_code_chapter": str_eq(data, "referral_code_set.primary_code_chapter", "Circulatory"),
        "narrative_match": bool_eq(data, "referral_code_set.narrative_match", True),
        "letter_choice": str_eq(
            data, "referral_letter_fields.diagnosis_summary_choice", "hfpef_with_exertional_dyspnea"
        ),
    }
    return all(checks.values()), checks


def check_allergy_details(data: Any) -> tuple[bool, dict[str, Any]]:
    allergies = list_of_dicts(data, "allergy_readiness.allergies")
    sulfa = next((item for item in allergies if norm(item.get("allergen")) == "sulfa antibiotics"), {})
    checks = {
        "readiness_status": str_eq(data, "allergy_readiness.readiness_status", "complete_documented"),
        "ready_for_letter": bool_eq(data, "allergy_readiness.ready_for_letter", True),
        "follow_up_needed": bool_eq(data, "allergy_readiness.follow_up_needed", False),
        "allergen": bool(sulfa),
        "reaction": norm(sulfa.get("reaction")) == "rash",
        "severity": norm(sulfa.get("severity")) == "moderate",
        "status": norm(sulfa.get("status")) == "active",
        "source": norm(sulfa.get("source")) == "referral_form",
        "letter_choice": str_eq(
            data, "referral_letter_fields.allergy_statement_choice", "active_sulfa_antibiotics_rash_moderate"
        ),
    }
    return all(checks.values()), checks


def check_recent_encounter(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "encounter_id": str_eq(data, "recent_encounter_evidence.encounter_id", "ENC-20177-20260211"),
        "date": str_eq(data, "recent_encounter_evidence.date", "2026-02-11"),
        "type": str_eq(data, "recent_encounter_evidence.type", "office_visit"),
        "provider_id": str_eq(data, "recent_encounter_evidence.provider_id", "PRV-PCP-002"),
        "signed_status": str_eq(data, "recent_encounter_evidence.signed_status", "signed"),
        "diagnosis_codes": has_all_strings(data, "recent_encounter_evidence.diagnosis_codes", {"I50.32", "R06.02"}),
        "medications_mentioned": has_all_strings(
            data, "recent_encounter_evidence.medications_mentioned", {"furosemide"}
        ),
        "care_plan_tag": str_eq(
            data, "recent_encounter_evidence.care_plan_tag", "cardiology_referral_for_hfpef_dyspnea"
        ),
        "letter_choice": str_eq(
            data, "referral_letter_fields.recent_encounter_choice", "pcp_2026_02_11_hfpef_dyspnea"
        ),
    }
    return all(checks.values()), checks


def check_echo_document(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "echo_received": bool_eq(data, "required_document_evidence.echo.received", True),
        "echo_document_id": str_eq(data, "required_document_evidence.echo.document_id", "DOC-ECHO-20177"),
        "echo_type": str_eq(data, "required_document_evidence.echo.type", "echocardiogram"),
        "echo_date": str_eq(data, "required_document_evidence.echo.date", "2025-11-12"),
        "echo_status": str_eq(data, "required_document_evidence.echo.status", "final"),
        "office_note_received": bool_eq(data, "required_document_evidence.office_note_received", True),
        "missing_required_documents": get(data, "required_document_evidence.missing_required_documents") == [],
        "letter_choice": str_eq(
            data, "referral_letter_fields.document_packet_choice", "final_echo_and_office_note_available"
        ),
    }
    return all(checks.values()), checks


def check_receiving_provider(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "provider_id": str_eq(data, "receiving_provider.provider_id", "PRV-CARD-020"),
        "name": str_eq(data, "receiving_provider.name", "Dr. Renee Okafor"),
        "role": str_eq(data, "receiving_provider.role", "Cardiologist"),
        "facility": str_eq(data, "receiving_provider.facility", "Summit Heart Center"),
        "phone": str_eq(data, "receiving_provider.phone", "555-430-2020"),
        "fax": str_eq(data, "receiving_provider.fax", "555-430-2299"),
        "letter_choice": str_eq(data, "referral_letter_fields.recipient_choice", "renee_okafor_summit_heart_center"),
    }
    return all(checks.values()), checks


def check_medication_highlight(data: Any) -> tuple[bool, dict[str, Any]]:
    medications = medication_map(data)
    furosemide = medications.get("furosemide", {})
    lisinopril = medications.get("lisinopril", {})
    checks = {
        "furosemide_present": bool(furosemide),
        "furosemide_active": norm(furosemide.get("status")) == "active",
        "furosemide_dose": norm(furosemide.get("dose")) == "20 mg",
        "furosemide_route": norm(furosemide.get("route")) == "oral",
        "furosemide_frequency": norm(furosemide.get("frequency")) == "daily",
        "furosemide_reason": norm(furosemide.get("highlight_reason")) == "heart_failure_diuretic",
        "lisinopril_present": bool(lisinopril),
        "lisinopril_reason": norm(lisinopril.get("highlight_reason")) == "blood_pressure_management",
        "letter_choice": str_eq(
            data, "referral_letter_fields.medication_summary_choice", "include_furosemide_and_lisinopril"
        ),
    }
    return all(checks.values()), checks


def check_authorization_readiness(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "authorization_status": str_eq(data, "authorization_readiness.authorization_status", "approved"),
        "referral_status": str_eq(data, "authorization_readiness.referral_status", "open"),
        "urgency": str_eq(data, "authorization_readiness.urgency", "routine"),
        "overall_readiness": str_eq(data, "authorization_readiness.overall_readiness", "ready_to_send"),
        "blocking_issues": get(data, "authorization_readiness.blocking_issues") == [],
        "authorization_letter_choice": str_eq(
            data, "referral_letter_fields.authorization_statement_choice", "authorization_approved"
        ),
        "readiness_letter_choice": str_eq(data, "referral_letter_fields.readiness_choice", "send_without_blocker"),
    }
    return all(checks.values()), checks


CHECKS: dict[str, Callable[[Any], tuple[bool, dict[str, Any]]]] = {
    "identity": check_identity,
    "clinical_diagnoses": check_clinical_diagnoses,
    "allergy_details": check_allergy_details,
    "recent_encounter": check_recent_encounter,
    "echo_document": check_echo_document,
    "receiving_provider": check_receiving_provider,
    "medication_highlight": check_medication_highlight,
    "authorization_readiness": check_authorization_readiness,
}


def load_candidate(path: Path) -> tuple[Any | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:  # noqa: BLE001 - evaluator reports parse/load errors as JSON.
        return None, f"{type(exc).__name__}: {exc}"


def main() -> int:
    candidate_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    data, error = load_candidate(candidate_path)
    total_weight = sum(point["weight"] for point in POINTS)

    if error is not None:
        details = []
        for point in POINTS:
            assigned = point["weight"] / total_weight
            details.append(
                {
                    "id": point["id"],
                    "goal": point["goal"],
                    "weight": point["weight"],
                    "assigned_score": round(assigned, 6),
                    "passed": False,
                    "earned_score": 0.0,
                    "details": {"error": error},
                }
            )
        print(json.dumps({"score": 0.0, "points": details}, indent=2, sort_keys=True))
        return 0

    earned_weight = 0
    details = []
    for point in POINTS:
        passed, check_details = CHECKS[point["id"]](data)
        if passed:
            earned_weight += point["weight"]
        assigned = point["weight"] / total_weight
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": round(assigned, 6),
                "passed": passed,
                "earned_score": round(assigned if passed else 0.0, 6),
                "details": check_details,
            }
        )

    score = earned_weight / total_weight
    print(json.dumps({"score": round(score, 6), "points": details}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
