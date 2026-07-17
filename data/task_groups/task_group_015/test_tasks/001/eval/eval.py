#!/usr/bin/env python3
"""Evaluator for task_group_015 test_001."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED = {
    "task_id": "test_001",
    "candidate_id": "DUP-TE-001",
    "merge_decision": {
        "disposition": "merge_ready_with_conflict_review",
        "canonical_target_patient_id": "P-73008",
        "source_patient_id": "P-11964",
        "manual_review_required": True,
        "reason_codes": {
            "active_duplicate_candidate",
            "canonical_record_has_lower_enterprise_mrn",
            "duplicate_record_already_points_to_target",
            "strong_identity_match",
            "suffix_nickname_discrepancy_present",
        },
    },
    "active_key_unions": {
        "condition_keys": {"copd", "hypertension", "right_knee_oa"},
        "medication_keys": {"amlodipine", "baseline_med", "tiotropium"},
        "allergy_keys": {"codeine", "shellfish"},
    },
    "identity_signals": {
        "match_signals": {
            "name_variant",
            "same_address_normalized",
            "same_dob",
            "same_insurance",
            "same_phone",
        },
        "conflict_signals": {"suffix_discrepancy"},
        "conflict_detail_codes": {
            "given_name_nickname_eleanor_vs_ellen",
            "suffix_present_only_on_target",
        },
    },
    "evidence": {
        "selected_audit_ids": {"AUD-TE-001-A"},
        "excluded_audit_ids": {"AUD-OTHER-MERGE"},
        "document_ids": {"DOC-PULM-11964"},
        "provider_ids": {"PRV-PCP-001", "PRV-PULM-030"},
    },
    "excluded_distractors": {
        "condition_keys": {"right_knee_oa"},
        "medication_keys": {"prednisone"},
        "audit_ids": {"AUD-OTHER-MERGE"},
    },
    "packet_readiness": {
        "ready_for_merge_packet": True,
        "readiness_status": "ready_with_review_note",
        "required_review_notes": {"suffix_nickname_discrepancy"},
    },
}


POINTS = [
    {
        "id": "source_target_disposition",
        "weight": 3,
        "description": "Correct merge disposition, canonical target/source, manual review flag, and disposition reason codes.",
    },
    {
        "id": "condition_union",
        "weight": 2,
        "description": "Correct normalized active condition key union.",
    },
    {
        "id": "medication_union",
        "weight": 2,
        "description": "Correct normalized active medication key union.",
    },
    {
        "id": "allergy_union",
        "weight": 1,
        "description": "Correct normalized active allergy key union.",
    },
    {
        "id": "match_conflict_signals",
        "weight": 2,
        "description": "Correct match signals and suffix/nickname conflict signals.",
    },
    {
        "id": "relevant_audit_evidence",
        "weight": 2,
        "description": "Correct relevant audit evidence selection.",
    },
    {
        "id": "irrelevant_audit_exclusion",
        "weight": 1,
        "description": "Correct exclusion of unrelated merge log.",
    },
    {
        "id": "packet_readiness_document_evidence",
        "weight": 3,
        "description": "Correct packet readiness, review note, documents, and provider evidence.",
    },
]


def as_obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def norm_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def norm_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


CONFLICT_DETAIL_ALIASES = {
    "given_name_eleanor_vs_ellen": "given_name_nickname_eleanor_vs_ellen",
    "given_name_variant_eleanor_vs_ellen": "given_name_nickname_eleanor_vs_ellen",
    "nickname_eleanor_vs_ellen": "given_name_nickname_eleanor_vs_ellen",
    "suffix_jr_absent_on_source": "suffix_present_only_on_target",
    "target_suffix_jr_source_suffix_missing": "suffix_present_only_on_target",
    "target_suffix_jr_source_no_suffix": "suffix_present_only_on_target",
}


def nested(answer: dict[str, Any], *keys: str) -> Any:
    current: Any = answer
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def set_detail(answer: dict[str, Any], path: tuple[str, ...], expected: set[str]) -> dict[str, Any]:
    actual = norm_set(nested(answer, *path))
    return {
        "expected": sorted(expected),
        "actual": sorted(actual),
        "missing": sorted(expected - actual),
        "extra": sorted(actual - expected),
    }


def normalized_alias_set(value: Any, aliases: dict[str, str]) -> set[str]:
    return {aliases.get(item, item) for item in norm_set(value)}


def set_detail_with_aliases(
    answer: dict[str, Any], path: tuple[str, ...], expected: set[str], aliases: dict[str, str]
) -> dict[str, Any]:
    actual = normalized_alias_set(nested(answer, *path), aliases)
    return {
        "expected": sorted(expected),
        "actual": sorted(actual),
        "missing": sorted(expected - actual),
        "extra": sorted(actual - expected),
    }


def check_source_target(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    md = as_obj(answer.get("merge_decision"))
    expected = EXPECTED["merge_decision"]
    checks = {
        "task_id": norm_scalar(answer.get("task_id")) == EXPECTED["task_id"],
        "candidate_id": norm_scalar(answer.get("candidate_id")) == EXPECTED["candidate_id"],
        "disposition": norm_scalar(md.get("disposition")) == expected["disposition"],
        "canonical_target_patient_id": norm_scalar(md.get("canonical_target_patient_id"))
        == expected["canonical_target_patient_id"],
        "source_patient_id": norm_scalar(md.get("source_patient_id")) == expected["source_patient_id"],
        "manual_review_required": md.get("manual_review_required") is expected["manual_review_required"],
        "reason_codes": norm_set(md.get("reason_codes")) == expected["reason_codes"],
    }
    return all(checks.values()), {"checks": checks, "actual_reason_codes": sorted(norm_set(md.get("reason_codes")))}


def check_exact_set(answer: dict[str, Any], path: tuple[str, ...], expected: set[str]) -> tuple[bool, dict[str, Any]]:
    detail = set_detail(answer, path, expected)
    return not detail["missing"] and not detail["extra"], detail


def check_match_conflict(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected = EXPECTED["identity_signals"]
    details = {
        "match_signals": set_detail(answer, ("identity_signals", "match_signals"), expected["match_signals"]),
        "conflict_signals": set_detail(answer, ("identity_signals", "conflict_signals"), expected["conflict_signals"]),
        "conflict_detail_codes": set_detail_with_aliases(
            answer,
            ("identity_signals", "conflict_detail_codes"),
            expected["conflict_detail_codes"],
            CONFLICT_DETAIL_ALIASES,
        ),
    }
    passed = all(not d["missing"] and not d["extra"] for d in details.values())
    return passed, details


def check_audit_exclusion(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    excluded_evidence = norm_set(nested(answer, "evidence", "excluded_audit_ids"))
    excluded_distractors = norm_set(nested(answer, "excluded_distractors", "audit_ids"))
    expected = EXPECTED["evidence"]["excluded_audit_ids"]
    selected = norm_set(nested(answer, "evidence", "selected_audit_ids"))
    combined = excluded_evidence | excluded_distractors
    passed = expected.issubset(combined) and not (expected & selected)
    return passed, {
        "expected_excluded": sorted(expected),
        "actual_evidence_excluded": sorted(excluded_evidence),
        "actual_distractor_excluded": sorted(excluded_distractors),
        "actual_selected_audit_ids": sorted(selected),
    }


def check_packet(answer: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    pr = as_obj(answer.get("packet_readiness"))
    expected = EXPECTED["packet_readiness"]
    document_detail = set_detail(answer, ("evidence", "document_ids"), EXPECTED["evidence"]["document_ids"])
    provider_detail = set_detail(answer, ("evidence", "provider_ids"), EXPECTED["evidence"]["provider_ids"])
    review_note_detail = set_detail(
        answer, ("packet_readiness", "required_review_notes"), expected["required_review_notes"]
    )
    review_notes = norm_set(pr.get("required_review_notes"))
    review_notes_pass = (not review_note_detail["missing"] and not review_note_detail["extra"]) or (
        "suffix_discrepancy_review" in review_notes and "given_name_variant_review" in review_notes
    )
    checks = {
        "ready_for_merge_packet": pr.get("ready_for_merge_packet") is expected["ready_for_merge_packet"],
        "readiness_status": norm_scalar(pr.get("readiness_status")) == expected["readiness_status"],
        "required_review_notes": review_notes_pass,
        "document_ids": not document_detail["missing"] and not document_detail["extra"],
        "provider_ids": not provider_detail["missing"] and not provider_detail["extra"],
    }
    return all(checks.values()), {
        "checks": checks,
        "document_ids": document_detail,
        "provider_ids": provider_detail,
        "required_review_notes": review_note_detail,
    }


def evaluate(answer: dict[str, Any]) -> dict[str, Any]:
    total_weight = sum(point["weight"] for point in POINTS)
    checks = {
        "source_target_disposition": check_source_target,
        "condition_union": lambda a: check_exact_set(
            a, ("active_key_unions", "condition_keys"), EXPECTED["active_key_unions"]["condition_keys"]
        ),
        "medication_union": lambda a: check_exact_set(
            a, ("active_key_unions", "medication_keys"), EXPECTED["active_key_unions"]["medication_keys"]
        ),
        "allergy_union": lambda a: check_exact_set(
            a, ("active_key_unions", "allergy_keys"), EXPECTED["active_key_unions"]["allergy_keys"]
        ),
        "match_conflict_signals": check_match_conflict,
        "relevant_audit_evidence": lambda a: check_exact_set(
            a, ("evidence", "selected_audit_ids"), EXPECTED["evidence"]["selected_audit_ids"]
        ),
        "irrelevant_audit_exclusion": check_audit_exclusion,
        "packet_readiness_document_evidence": check_packet,
    }
    point_results = []
    score = 0.0
    for point in POINTS:
        passed, detail = checks[point["id"]](answer)
        assigned = point["weight"] / total_weight
        earned = assigned if passed else 0.0
        score += earned
        point_results.append(
            {
                "id": point["id"],
                "description": point["description"],
                "weight": point["weight"],
                "assigned_score": assigned,
                "passed": passed,
                "earned_score": earned,
                "details": detail,
            }
        )
    return {
        "score": score,
        "points": point_results,
    }


def main() -> int:
    if len(sys.argv) > 2:
        print(json.dumps({"score": 0.0, "error": "usage: eval.py <candidate_answer.json>"}))
        return 2
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        with path.open("r", encoding="utf-8") as handle:
            answer = json.load(handle)
    except Exception as exc:  # noqa: BLE001 - evaluator should return JSON for all parse/read failures.
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "points": [],
                    "error": f"failed to read candidate answer: {exc}",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    if not isinstance(answer, dict):
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "points": [],
                    "error": "candidate answer must be a JSON object",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(evaluate(answer), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
