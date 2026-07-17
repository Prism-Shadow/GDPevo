"""Train-only judge helper for the task_group_015 environment."""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import Any, Callable


NOTICE = "train-only judge; no gold answers or rubric details are returned"
REF_MAR_RE = re.compile(r"REF-MAR-[0-9]{3}(?:-DUP)?")


def get(value: Any, path: str, default: Any = None) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def norm(value: Any) -> str:
    return str(value).strip()


def norm_lower(value: Any) -> str:
    return norm(value).lower()


def norm_set(value: Any) -> set[str]:
    if isinstance(value, list):
        return {norm(item) for item in value if norm(item)}
    if isinstance(value, set):
        return {norm(item) for item in value if norm(item)}
    if isinstance(value, str):
        return {value.strip()} if value.strip() else set()
    return set()


def lower_set(value: Any) -> set[str]:
    return {item.lower() for item in norm_set(value)}


def refs_in(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str):
        found.update(REF_MAR_RE.findall(value))
    elif isinstance(value, list):
        for item in value:
            found.update(refs_in(item))
    elif isinstance(value, dict):
        for item in value.values():
            found.update(refs_in(item))
    return found


def dict_list_by(value: Any, key: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in value:
        if isinstance(item, dict) and norm(item.get(key)):
            result[norm(item.get(key))] = item
    return result


def list_has_dict(value: Any, **expected: Any) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if not isinstance(item, dict):
            continue
        if all(item.get(key) == expected_value for key, expected_value in expected.items()):
            return True
    return False


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


class JudgeAPI:
    """Scores train answers without exposing gold data or rubric details."""

    def __init__(self, data: dict):
        self.data = data
        self.scorers: dict[str, list[tuple[int, Callable[[Any], bool]]]] = {
            "train_001": self._train_001_points(),
            "train_002": self._train_002_points(),
            "train_003": self._train_003_points(),
            "train_004": self._train_004_points(),
            "train_005": self._train_005_points(),
        }

    def handle(self, body: dict) -> tuple[dict, int]:
        task_id = body.get("task_id")
        answer = body.get("answer")
        if not isinstance(task_id, str):
            return {"score": 0.0, "correct": False, "notice": NOTICE}, HTTPStatus.BAD_REQUEST
        if task_id.startswith("test_"):
            return {"score": 0.0, "correct": False, "notice": NOTICE}, HTTPStatus.FORBIDDEN
        if task_id not in self.scorers:
            return {"score": 0.0, "correct": False, "notice": NOTICE}, HTTPStatus.NOT_FOUND
        if answer is None:
            return {"score": 0.0, "correct": False, "notice": NOTICE}, HTTPStatus.BAD_REQUEST
        checks = self.scorers[task_id]
        total = sum(weight for weight, _ in checks)
        earned = sum(weight for weight, predicate in checks if predicate(answer))
        score = round(earned / total, 6) if total else 0.0
        return {"score": score, "correct": score >= 0.999999, "notice": NOTICE}, HTTPStatus.OK

    def _train_001_points(self) -> list[tuple[int, Callable[[Any], bool]]]:
        return [
            (
                3,
                lambda a: get(a, "candidate_id") == "DUP-TR-001"
                and get(a, "merge.target_patient_id") == "P-31014"
                and get(a, "merge.source_patient_id") == "P-88420"
                and get(a, "merge.disposition") == "ready_to_merge",
            ),
            (
                2,
                lambda a: get(a, "merge_decision.disposition") == "merge_ready"
                and get(a, "merge_decision.canonical_target_patient_id") == "P-31014"
                and get(a, "merge_decision.source_patient_id") == "P-88420"
                and get(a, "merge_decision.manual_review_required") is False
                and get(a, "packet_readiness.ready_for_merge_packet") is True
                and get(a, "packet_readiness.readiness_status") == "ready",
            ),
            (
                2,
                lambda a: norm_set(get(a, "clinical_unions.active_condition_keys"))
                == {"copd", "coronary_artery_disease", "diabetes_type_2", "hypertension", "right_knee_oa"},
            ),
            (
                2,
                lambda a: norm_set(get(a, "clinical_unions.active_medication_keys"))
                == {"aspirin", "baseline_med", "metformin"},
            ),
            (
                2,
                lambda a: norm_set(get(a, "clinical_unions.active_allergy_keys"))
                == {"baseline_allergy", "iodinated_contrast", "penicillin"},
            ),
            (
                2,
                lambda a: norm_set(get(a, "identity_signals.match_signals"))
                == {"name_variant", "same_dob", "same_insurance", "same_phone", "shared_external_cardiology_document"}
                and norm_set(get(a, "identity_signals.conflict_signals")) == {"address_abbreviation"},
            ),
            (2, lambda a: norm_set(get(a, "evidence.document_ids")) == {"DOC-CARD-TR-001", "DOC-MERGE-TR-001-A"}),
            (2, lambda a: norm_set(get(a, "evidence.audit_ids")) == {"AUD-TR-001-A", "AUD-TR-001-B"}),
            (
                2,
                lambda a: norm_set(get(a, "excluded_distractors.condition_keys")) == {"left_knee_oa"}
                and norm_set(get(a, "excluded_distractors.medication_keys")) == {"naproxen"}
                and norm_set(get(a, "excluded_distractors.document_ids")) == {"DOC-2B6141CA", "DOC-E1547158"}
                and norm_set(get(a, "excluded_distractors.audit_ids")) == set(),
            ),
            (
                1,
                lambda a: get(a, "packet_contact.specialist_provider.provider_id") == "PRV-CARD-020"
                and get(a, "packet_contact.specialist_provider.facility") == "Summit Heart Center"
                and get(a, "packet_contact.specialist_provider.fax") == "555-430-2299",
            ),
        ]

    def _train_002_points(self) -> list[tuple[int, Callable[[Any], bool]]]:
        return [
            (
                2,
                lambda a: get(a, "patient_referral.patient_id") == "P-20177"
                and get(a, "patient_referral.referral_id") == "REF-FEB-CARD-007"
                and get(a, "patient_referral.batch_id") == "FEB26-CARD"
                and get(a, "patient_referral.service_line") == "cardiology"
                and get(a, "patient_referral.requested_date") == "2026-02-15",
            ),
            (
                2,
                lambda a: {
                    norm(item.get("normalized_key"))
                    for item in get(a, "active_diagnoses", [])
                    if isinstance(item, dict)
                }
                == {"diabetes_type_2", "hypertension", "heart_failure_diastolic", "right_knee_oa", "dyspnea"}
                and get(a, "referral_code_set.primary_code") == "I50.32"
                and norm_set(get(a, "referral_code_set.supporting_codes")) == {"R06.02"}
                and get(a, "referral_code_set.icd_validation") == "valid_matches_narrative",
            ),
            (
                2,
                lambda a: get(a, "allergy_readiness.readiness_status") == "complete_documented"
                and get(a, "allergy_readiness.ready_for_letter") is True
                and list_has_dict(
                    get(a, "allergy_readiness.allergies"),
                    allergen="sulfa antibiotics",
                    reaction="rash",
                    severity="moderate",
                    status="active",
                ),
            ),
            (
                2,
                lambda a: get(a, "recent_encounter_evidence.encounter_id") == "ENC-20177-20260211"
                and get(a, "recent_encounter_evidence.date") == "2026-02-11"
                and norm_set(get(a, "recent_encounter_evidence.diagnosis_codes")) == {"I50.32", "R06.02"}
                and lower_set(get(a, "recent_encounter_evidence.medications_mentioned")) == {"furosemide"},
            ),
            (
                2,
                lambda a: get(a, "required_document_evidence.echo.received") is True
                and get(a, "required_document_evidence.echo.document_id") == "DOC-ECHO-20177"
                and get(a, "required_document_evidence.echo.status") == "final"
                and get(a, "required_document_evidence.office_note_received") is True
                and norm_set(get(a, "required_document_evidence.missing_required_documents")) == set(),
            ),
            (
                2,
                lambda a: get(a, "receiving_provider.provider_id") == "PRV-CARD-020"
                and get(a, "receiving_provider.facility") == "Summit Heart Center"
                and get(a, "receiving_provider.fax") == "555-430-2299",
            ),
            (
                1,
                lambda a: set(dict_list_by(get(a, "medication_highlights"), "medication"))
                == {"furosemide", "lisinopril"},
            ),
            (
                2,
                lambda a: get(a, "authorization_readiness.authorization_status") == "approved"
                and get(a, "authorization_readiness.overall_readiness") == "ready_to_send"
                and norm_set(get(a, "authorization_readiness.blocking_issues")) == set()
                and get(a, "referral_letter_fields.readiness_choice") == "send_without_blocker",
            ),
        ]

    def _train_003_points(self) -> list[tuple[int, Callable[[Any], bool]]]:
        return [
            (
                2,
                lambda a: get(a, "patient.patient_id") == "P-44702"
                and get(a, "patient.enterprise_mrn") == "E10044702"
                and get(a, "recipient.provider_id") == "PRV-ORTHO-010",
            ),
            (
                2,
                lambda a: norm_set(get(a, "active_condition_keys"))
                == {"diabetes_type_2", "hypertension", "memory_loss", "right_hip_oa", "right_knee_oa"},
            ),
            (
                2,
                lambda a: norm_set(get(a, "active_medication_keys"))
                == {"acetaminophen", "baseline_med", "insulin_glargine"},
            ),
            (1, lambda a: norm_set(get(a, "active_allergy_keys")) == {"baseline_allergy", "latex"}),
            (
                3,
                lambda a: [
                    item.get("encounter_id") for item in get(a, "handoff_encounters", []) if isinstance(item, dict)
                ]
                == ["ENC-44702-0", "ENC-44702-1", "ENC-44702-2", "ENC-44702-3"],
            ),
            (
                3,
                lambda a: get(a, "source_selection.selection_basis") == "orthopedic_surgical_handoff_window"
                and norm_set(get(a, "source_selection.selected_encounter_ids"))
                == {"ENC-44702-0", "ENC-44702-1", "ENC-44702-2", "ENC-44702-3"}
                and norm_set(get(a, "source_selection.excluded_encounter_ids"))
                == {"ENC-0460F33D", "ENC-0FE06CF3", "ENC-44702-4", "ENC-FA393BB8"},
            ),
            (
                1,
                lambda a: get(a, "latest_immunization.immunization_id") == "IMM-1372CDAF"
                and get(a, "latest_immunization.date") == "2026-03-11",
            ),
            (
                2,
                lambda a: get(a, "disclosure.disclosure_id") == "DISC-44702-ORTHO"
                and get(a, "disclosure.status") == "permitted"
                and get(a, "disclosure.recipient_provider_id") == "PRV-ORTHO-010",
            ),
            (
                3,
                lambda a: norm_set(get(a, "risk_flags"))
                == {
                    "cognitive_memory_loss",
                    "fall_risk_note_required",
                    "hypertension",
                    "insulin_dependent_diabetes",
                    "latex_allergy",
                    "perioperative_glucose_plan_needed",
                }
                and get(a, "packet_readiness.status") == "ready_with_risk_flags"
                and get(a, "packet_readiness.ready_to_send") is True,
            ),
            (
                3,
                lambda a: set(dict_list_by(get(a, "risk_flag_evidence"), "risk_flag"))
                == {
                    "cognitive_memory_loss",
                    "fall_risk_note_required",
                    "hypertension",
                    "insulin_dependent_diabetes",
                    "latex_allergy",
                    "perioperative_glucose_plan_needed",
                },
            ),
        ]

    def _train_004_points(self) -> list[tuple[int, Callable[[Any], bool]]]:
        def validations(a: Any) -> dict[Any, Any]:
            return {
                row.get("code"): row
                for row in get(a, "service_request.reason_code_validation", [])
                if isinstance(row, dict)
            }

        return [
            (
                2,
                lambda a: get(a, "duplicate_review.candidate_id") == "DUP-TR-004"
                and get(a, "duplicate_review.candidate_status") == "needs_review"
                and get(a, "duplicate_review.decision") == "review_hold"
                and get(a, "duplicate_review.merge_target_patient_id") is None
                and get(a, "duplicate_review.merge_source_patient_id") is None,
            ),
            (
                2,
                lambda a: norm_set(get(a, "duplicate_review.conflict_signals"))
                == {"different_given_name", "different_phone", "opposite_laterality_problem"}
                and norm_set(get(a, "duplicate_review.match_signals"))
                == {"same_dob", "same_insurance", "similar_address"},
            ),
            (
                2,
                lambda a: get(a, "service_request.service_request_id") == "SR-TR-004"
                and get(a, "service_request.patient_id") == "P-55218"
                and get(a, "service_request.service_code") == "ORTHO-CONSULT"
                and get(a, "service_request.service_code_valid") is True,
            ),
            (
                2,
                lambda a: get(a, "service_request.status") == "active"
                and get(a, "service_request.intent") == "order"
                and get(a, "service_request.priority") == "routine"
                and get(a, "service_request.authored_on") == "2026-03-04"
                and get(a, "service_request.occurrence_date") == "2026-03-20",
            ),
            (
                2,
                lambda a: norm_set(get(a, "service_request.reason_codes")) == {"M17.11", "S83.241A"}
                and validations(a).get("M17.11", {}).get("chapter") == "Musculoskeletal"
                and validations(a).get("M17.11", {}).get("matches_patient_evidence") is True
                and validations(a).get("S83.241A", {}).get("chapter") == "Injury"
                and validations(a).get("S83.241A", {}).get("matches_patient_evidence") is True,
            ),
            (
                2,
                lambda a: get(a, "sbar_coverage.complete") is True
                and norm_set(get(a, "sbar_coverage.sections_present"))
                == {"situation", "background", "assessment", "recommendation"}
                and norm_set(get(a, "sbar_coverage.missing_sections")) == set(),
            ),
            (
                2,
                lambda a: get(a, "service_request.requester_provider_id") == "PRV-PCP-002"
                and get(a, "service_request.performer_provider_id") == "PRV-ORTHO-011"
                and get(a, "service_request.performer_service_line") == "orthopedics",
            ),
        ]

    def _train_005_points(self) -> list[tuple[int, Callable[[Any], bool]]]:
        invalid = {
            "REF-MAR-001",
            "REF-MAR-003",
            "REF-MAR-005",
            "REF-MAR-006",
            "REF-MAR-011",
            "REF-MAR-012",
            "REF-MAR-015",
            "REF-MAR-017",
            "REF-MAR-018",
            "REF-MAR-019-DUP",
        }
        mismatch = {
            "REF-MAR-001",
            "REF-MAR-002",
            "REF-MAR-003",
            "REF-MAR-005",
            "REF-MAR-006",
            "REF-MAR-007",
            "REF-MAR-009",
            "REF-MAR-011",
            "REF-MAR-012",
            "REF-MAR-013",
            "REF-MAR-014",
            "REF-MAR-015",
            "REF-MAR-016",
            "REF-MAR-017",
            "REF-MAR-018",
        }
        queues = {
            "authorization_missing": {"REF-MAR-001", "REF-MAR-005", "REF-MAR-009", "REF-MAR-013", "REF-MAR-017"},
            "authorization_pending": set(),
            "records_request": {
                "REF-MAR-001",
                "REF-MAR-002",
                "REF-MAR-008",
                "REF-MAR-011",
                "REF-MAR-012",
                "REF-MAR-013",
                "REF-MAR-017",
                "REF-MAR-018",
            },
            "imaging_follow_up": {
                "REF-MAR-001",
                "REF-MAR-003",
                "REF-MAR-005",
                "REF-MAR-006",
                "REF-MAR-007",
                "REF-MAR-009",
                "REF-MAR-010",
                "REF-MAR-011",
                "REF-MAR-015",
                "REF-MAR-017",
                "REF-MAR-018",
            },
        }
        tiers = {
            "tier_1_immediate": {"REF-MAR-004", "REF-MAR-009", "REF-MAR-015", "REF-MAR-019-DUP"},
            "tier_2_short_term": {
                "REF-MAR-001",
                "REF-MAR-002",
                "REF-MAR-003",
                "REF-MAR-005",
                "REF-MAR-006",
                "REF-MAR-007",
                "REF-MAR-011",
                "REF-MAR-012",
                "REF-MAR-013",
                "REF-MAR-014",
                "REF-MAR-016",
                "REF-MAR-017",
                "REF-MAR-018",
            },
            "tier_3_administrative": {"REF-MAR-008", "REF-MAR-010"},
        }
        summary = {
            "total_referral_rows": 19,
            "unique_patients": 18,
            "urgent_count": 4,
            "routine_count": 15,
            "invalid_or_out_of_range_count": 10,
            "mismatch_count": 15,
            "duplicate_group_count": 1,
            "insurance_patient_anomaly_count": 1,
            "authorization_missing_count": 5,
            "authorization_pending_count": 0,
            "records_request_count": 8,
            "imaging_follow_up_count": 11,
            "tier_1_count": 4,
            "tier_2_count": 13,
            "tier_3_count": 2,
            "validated_ready_no_follow_up_count": 0,
        }
        return [
            (
                3,
                lambda a: get(a, "batch.batch_id") == "MAR26-ORTHO-A"
                and get(a, "batch.service_line") == "orthopedics"
                and as_int(get(a, "batch.record_count")) == 19
                and as_int(get(a, "batch.unique_patient_count")) == 18,
            ),
            (3, lambda a: refs_in(get(a, "invalid_or_out_of_range_code_referrals")) == invalid),
            (2, lambda a: refs_in(get(a, "laterality_or_narrative_mismatch_referrals")) == mismatch),
            (
                2,
                lambda a: any(
                    isinstance(group, dict)
                    and group.get("patient_id") == "P-55218"
                    and refs_in(group.get("referral_ids", group)) == {"REF-MAR-004", "REF-MAR-019-DUP"}
                    for group in get(a, "duplicate_groups", [])
                ),
            ),
            (
                2,
                lambda a: any(
                    isinstance(row, dict)
                    and row.get("anomaly_id") == "ANOM-MAR-INS-881144"
                    and norm_set(row.get("patient_ids")) == {"P-55218", "P-55281"}
                    and refs_in(row.get("referral_ids", row)) == {"REF-MAR-003", "REF-MAR-004", "REF-MAR-019-DUP"}
                    and row.get("insurance_id") == "INS-881144"
                    for row in get(a, "insurance_patient_anomalies", [])
                ),
            ),
            (
                2,
                lambda a: all(
                    refs_in(get(a, f"follow_up_queues.{key}")) == expected for key, expected in queues.items()
                ),
            ),
            (2, lambda a: refs_in(get(a, "action_plan.tier_1_immediate")) == tiers["tier_1_immediate"]),
            (2, lambda a: refs_in(get(a, "action_plan.tier_2_short_term")) == tiers["tier_2_short_term"]),
            (2, lambda a: refs_in(get(a, "action_plan.tier_3_administrative")) == tiers["tier_3_administrative"]),
            (
                2,
                lambda a: all(
                    as_int(get(a, f"summary_counts.{key}")) == expected for key, expected in summary.items()
                ),
            ),
        ]
