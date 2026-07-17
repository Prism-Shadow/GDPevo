#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable


POINTS: list[dict[str, Any]] = [
    {
        "id": "identity",
        "weight": 1,
        "goal": "Correct patient/referral identity and referral header fields.",
    },
    {
        "id": "pulmonary_diagnoses",
        "weight": 3,
        "goal": "Correct active pulmonary diagnosis set, deduplicated COPD evidence, and ICD validation.",
    },
    {
        "id": "respiratory_medications",
        "weight": 2,
        "goal": "Correct active respiratory medication highlights and exclusion of non-respiratory active medication.",
    },
    {
        "id": "allergy_completeness",
        "weight": 2,
        "goal": "Correct active levofloxacin allergy details and completeness classification.",
    },
    {
        "id": "recent_encounter",
        "weight": 2,
        "goal": "Correct most relevant signed pulmonology referral encounter evidence.",
    },
    {
        "id": "documents_spirometry",
        "weight": 3,
        "goal": "Correct existing chest X-ray/office-note evidence and missing spirometry blocker.",
    },
    {
        "id": "receiving_provider",
        "weight": 1,
        "goal": "Correct receiving pulmonology provider and directory fields.",
    },
    {
        "id": "authorization_readiness",
        "weight": 2,
        "goal": "Correct authorization status, urgency, readiness tier, blockers, and letter choices.",
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
    return {norm(value) for value in values}


def has_all_strings(data: Any, path: str, expected: set[str]) -> bool:
    return string_set(get(data, path, [])) == {norm(value) for value in expected}


def diagnosis_map(data: Any) -> dict[str, dict[str, Any]]:
    return {
        norm(item.get("normalized_key")): item
        for item in list_of_dicts(data, "active_pulmonary_diagnoses")
        if norm(item.get("normalized_key"))
    }


def medication_map(data: Any) -> dict[str, dict[str, Any]]:
    return {
        norm(item.get("medication")): item
        for item in list_of_dicts(data, "active_respiratory_medications")
        if norm(item.get("medication"))
    }


def check_identity(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "patient_id": str_eq(data, "patient_referral.patient_id", "P-66591"),
        "referral_id": str_eq(data, "patient_referral.referral_id", "REF-APR-PULM-004"),
        "batch_id": str_eq(data, "patient_referral.batch_id", "APR26-PULM"),
        "service_line": str_eq(data, "patient_referral.service_line", "pulmonology"),
        "requested_date": str_eq(data, "patient_referral.requested_date", "2026-04-15"),
    }
    return all(checks.values()), checks


def check_pulmonary_diagnoses(data: Any) -> tuple[bool, dict[str, Any]]:
    diagnoses = diagnosis_map(data)
    copd = diagnoses.get("copd", {})
    asthma = diagnoses.get("asthma_moderate_persistent", {})
    dyspnea = diagnoses.get("dyspnea", {})
    checks = {
        "active_pulmonary_key_set": set(diagnoses) == {"copd", "asthma_moderate_persistent", "dyspnea"},
        "copd_code": norm(copd.get("code")) == "j44.9",
        "copd_condition_ids": string_set(copd.get("condition_ids")) == {"cond-88307ea8", "cond-e6a76d09"},
        "copd_role": norm(copd.get("role")) == "primary_referral_diagnosis",
        "asthma_code": norm(asthma.get("code")) == "j45.40",
        "dyspnea_code": norm(dyspnea.get("code")) == "r06.02",
        "all_referral_relevant": all(item.get("referral_relevant") is True for item in [copd, asthma, dyspnea]),
        "primary_code": str_eq(data, "referral_code_set.primary_code", "J44.9"),
        "supporting_codes": has_all_strings(data, "referral_code_set.supporting_codes", {"J45.40", "R06.02"}),
        "icd_validation": str_eq(data, "referral_code_set.icd_validation", "valid_matches_narrative"),
        "primary_code_chapter": str_eq(data, "referral_code_set.primary_code_chapter", "Respiratory"),
        "narrative_match": bool_eq(data, "referral_code_set.narrative_match", True),
        "letter_choice": str_eq(
            data, "referral_letter_fields.diagnosis_summary_choice", "primary_referral_diagnosis_with_symptom"
        ),
    }
    return all(checks.values()), checks


def check_respiratory_medications(data: Any) -> tuple[bool, dict[str, Any]]:
    medications = medication_map(data)
    fluticasone = medications.get("fluticasone/salmeterol", {})
    albuterol = medications.get("albuterol inhaler", {})
    checks = {
        "medication_set": set(medications) == {"fluticasone/salmeterol", "albuterol inhaler"},
        "fluticasone_status": norm(fluticasone.get("status")) == "active",
        "fluticasone_dose": norm(fluticasone.get("dose")) == "250/50 mcg",
        "fluticasone_route": norm(fluticasone.get("route")) == "inhaled",
        "fluticasone_frequency": norm(fluticasone.get("frequency")) == "twice daily",
        "fluticasone_reason": norm(fluticasone.get("highlight_reason")) == "controller_inhaler",
        "albuterol_status": norm(albuterol.get("status")) == "active",
        "albuterol_dose": norm(albuterol.get("dose")) == "2 puffs",
        "albuterol_route": norm(albuterol.get("route")) == "inhaled",
        "albuterol_frequency": norm(albuterol.get("frequency")) == "as needed",
        "albuterol_reason": norm(albuterol.get("highlight_reason")) == "rescue_inhaler",
        "letter_choice": str_eq(
            data,
            "referral_letter_fields.medication_summary_choice",
            "include_controller_and_rescue_therapy",
        ),
    }
    return all(checks.values()), checks


def check_allergy_completeness(data: Any) -> tuple[bool, dict[str, Any]]:
    allergies = list_of_dicts(data, "allergy_readiness.allergies")
    levofloxacin = next((item for item in allergies if norm(item.get("allergen")) == "levofloxacin"), {})
    checks = {
        "readiness_status": str_eq(data, "allergy_readiness.readiness_status", "complete_documented"),
        "ready_for_letter": bool_eq(data, "allergy_readiness.ready_for_letter", True),
        "follow_up_needed": bool_eq(data, "allergy_readiness.follow_up_needed", False),
        "allergen_present": bool(levofloxacin),
        "reaction": norm(levofloxacin.get("reaction")) == "tendon pain",
        "severity": norm(levofloxacin.get("severity")) == "moderate",
        "status": norm(levofloxacin.get("status")) == "active",
        "source": norm(levofloxacin.get("source")) == "referral_form",
        "letter_choice": str_eq(
            data,
            "referral_letter_fields.allergy_statement_choice",
            "documented_active_allergy",
        ),
    }
    return all(checks.values()), checks


def check_recent_encounter(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "encounter_id": str_eq(data, "recent_encounter_evidence.encounter_id", "ENC-66591-20260406"),
        "date": str_eq(data, "recent_encounter_evidence.date", "2026-04-06"),
        "type": str_eq(data, "recent_encounter_evidence.type", "office_visit"),
        "provider_id": str_eq(data, "recent_encounter_evidence.provider_id", "PRV-PCP-002"),
        "signed_status": str_eq(data, "recent_encounter_evidence.signed_status", "signed"),
        "diagnosis_codes": has_all_strings(data, "recent_encounter_evidence.diagnosis_codes", {"J44.9", "R06.02"}),
        "medications_mentioned": has_all_strings(
            data,
            "recent_encounter_evidence.medications_mentioned",
            {"fluticasone/salmeterol", "albuterol inhaler"},
        ),
        "care_plan_tag": str_eq(
            data,
            "recent_encounter_evidence.care_plan_tag",
            "pulmonology_referral_for_copd_dyspnea",
        ),
        "letter_choice": str_eq(
            data, "referral_letter_fields.recent_encounter_choice", "most_relevant_signed_referral_encounter"
        ),
    }
    return all(checks.values()), checks


def check_documents_spirometry(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "chest_xray_received": bool_eq(data, "document_readiness.chest_xray.received", True),
        "chest_xray_document_id": str_eq(data, "document_readiness.chest_xray.document_id", "DOC-CXR-66591"),
        "chest_xray_type": str_eq(data, "document_readiness.chest_xray.type", "chest_xray"),
        "chest_xray_date": str_eq(data, "document_readiness.chest_xray.date", "2026-03-30"),
        "chest_xray_status": str_eq(data, "document_readiness.chest_xray.status", "final"),
        "office_note_received": bool_eq(data, "document_readiness.office_note_received", True),
        "office_note_source": str_eq(data, "document_readiness.office_note_source", "signed_encounter"),
        "pulmonary_function_test_received": bool_eq(
            data, "document_readiness.pulmonary_function_test.received", False
        ),
        "pulmonary_function_test_document_id_null": get(data, "document_readiness.pulmonary_function_test.document_id")
        is None,
        "pulmonary_function_test_status": str_eq(data, "document_readiness.pulmonary_function_test.status", "missing"),
        "missing_required_documents": has_all_strings(
            data, "document_readiness.missing_required_documents", {"pulmonary_function_test"}
        ),
        "letter_choice": str_eq(
            data,
            "referral_letter_fields.document_packet_choice",
            "requires_document_follow_up",
        ),
    }
    return all(checks.values()), checks


def check_receiving_provider(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "provider_id": str_eq(data, "receiving_provider.provider_id", "PRV-PULM-030"),
        "name": str_eq(data, "receiving_provider.name", "Dr. Leo Navarro"),
        "role": str_eq(data, "receiving_provider.role", "Pulmonologist"),
        "facility": str_eq(data, "receiving_provider.facility", "Northgate Pulmonary Clinic"),
        "phone": str_eq(data, "receiving_provider.phone", "555-440-3030"),
        "fax": str_eq(data, "receiving_provider.fax", "555-440-3399"),
        "letter_choice": str_eq(
            data,
            "referral_letter_fields.recipient_choice",
            "receiving_specialist_from_referral",
        ),
    }
    return all(checks.values()), checks


def check_authorization_readiness(data: Any) -> tuple[bool, dict[str, Any]]:
    checks = {
        "authorization_status": str_eq(data, "authorization_readiness.authorization_status", "pending"),
        "referral_status": str_eq(data, "authorization_readiness.referral_status", "open"),
        "urgency": str_eq(data, "authorization_readiness.urgency", "urgent"),
        "readiness_tier": str_eq(data, "authorization_readiness.readiness_tier", "Tier 1"),
        "overall_readiness": str_eq(data, "authorization_readiness.overall_readiness", "hold_for_missing_documents"),
        "blocking_issues": has_all_strings(
            data,
            "authorization_readiness.blocking_issues",
            {"authorization_pending", "pulmonary_function_test_missing"},
        ),
        "authorization_letter_choice": str_eq(
            data,
            "referral_letter_fields.authorization_statement_choice",
            "authorization_pending",
        ),
        "readiness_letter_choice": str_eq(
            data,
            "referral_letter_fields.readiness_choice",
            "hold_for_missing_required_document",
        ),
    }
    return all(checks.values()), checks


CHECKS: dict[str, Callable[[Any], tuple[bool, dict[str, Any]]]] = {
    "identity": check_identity,
    "pulmonary_diagnoses": check_pulmonary_diagnoses,
    "respiratory_medications": check_respiratory_medications,
    "allergy_completeness": check_allergy_completeness,
    "recent_encounter": check_recent_encounter,
    "documents_spirometry": check_documents_spirometry,
    "receiving_provider": check_receiving_provider,
    "authorization_readiness": check_authorization_readiness,
}


def load_candidate(path: Path) -> tuple[Any | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except Exception as exc:  # noqa: BLE001 - evaluator reports parse/load errors as JSON.
        return None, f"{type(exc).__name__}: {exc}"


def main() -> int:
    if len(sys.argv) > 2:
        print(json.dumps({"score": 0.0, "error": "usage: eval.py [candidate_answer.json]", "points": []}, indent=2))
        return 2

    candidate_path = (
        Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
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
