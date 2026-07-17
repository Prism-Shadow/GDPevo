#!/usr/bin/env python3
"""Evaluate test tasks with exact, non-overlapping business-result bundles.

Each rubric point owns a disjoint set of required answer paths. The complete
bundle must match the standard answer for the point to receive its full
normalized score; otherwise the point receives zero.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


POINT_SPECS: dict[str, list[dict[str, Any]]] = {
    "test_001": [
        {
            "point_id": "SP001",
            "weight": 3,
            "goal": "Exact population quality accounting, quarantine population, and country rollup.",
            "paths": ["quality_summary", "quarantine_row_ids", "country_rollup"],
        },
        {
            "point_id": "SP002",
            "weight": 2,
            "goal": "Exact focus-case identity controls, evidence memberships, and master decisions.",
            "paths": [
                "focus_cases[].focus_case_id",
                "focus_cases[].seed_row_id",
                "focus_cases[].internal_controls.identity_code",
                "focus_cases[].identity_resolution",
            ],
        },
        {
            "point_id": "SP003",
            "weight": 1,
            "goal": "Exact canonical contact outcomes for all focus cases.",
            "paths": ["focus_cases[].canonical_contact"],
        },
        {
            "point_id": "SP004",
            "weight": 3,
            "goal": "Exact field-provenance controls, selected sources, and precedence reasons.",
            "paths": [
                "focus_cases[].internal_controls.field_provenance_code",
                "focus_cases[].field_provenance",
            ],
        },
        {
            "point_id": "SP005",
            "weight": 1,
            "goal": "Exact renewal-readiness controls, ready population, and certification action.",
            "paths": [
                "focus_cases[].internal_controls.outreach_code",
                "focus_cases[].renewal_readiness",
                "renewal_ready_master_ids",
                "certification_status",
            ],
        },
        {
            "point_id": "SP006",
            "weight": 1,
            "goal": "Exact unsafe-identity baseline graph.",
            "paths": [
                "unsafe_identity_containment_robustness.policy_id",
                "unsafe_identity_containment_robustness.original_graph",
            ],
        },
        {
            "point_id": "SP007",
            "weight": 1,
            "goal": "Exact minimum containment repair and source-withdrawal robustness results.",
            "paths": [
                "unsafe_identity_containment_robustness.minimum_containment_repair",
                "unsafe_identity_containment_robustness.source_withdrawal_checks",
                "unsafe_identity_containment_robustness.summary",
            ],
        },
        {
            "point_id": "SP008",
            "weight": 3,
            "goal": "Exact FX basis, candidate recovery batches, and batch costs.",
            "paths": [
                "fx_budgeted_evidence_recovery.recovery_id",
                "fx_budgeted_evidence_recovery.fx_basis",
                "fx_budgeted_evidence_recovery.candidate_batches",
            ],
        },
        {
            "point_id": "SP009",
            "weight": 1,
            "goal": "Exact initial-state assessment and selected two-stage evidence-recovery plan.",
            "paths": [
                "fx_budgeted_evidence_recovery.initial_state",
                "fx_budgeted_evidence_recovery.plan_search",
            ],
        },
        {
            "point_id": "SP010",
            "weight": 2,
            "goal": "Exact all-permutation source-sequence stability audit.",
            "paths": [
                "source_sequence_release_stability_audit.audit_id",
                "source_sequence_release_stability_audit.order_results",
                "source_sequence_release_stability_audit.summary",
            ],
        },
    ],
    "test_002": [
        {
            "point_id": "SP001",
            "weight": 3,
            "goal": "Exact authoritative source and scoped source-population counts.",
            "paths": [
                "audit_summary.collection_id",
                "audit_summary.cutoff_at",
                "audit_summary.authoritative_snapshot_id",
                "audit_summary.raw_row_count",
                "audit_summary.logical_transaction_count",
                "audit_summary.duplicate_raw_count",
            ],
        },
        {
            "point_id": "SP002",
            "weight": 1,
            "goal": "Exact exception accounting and mismatch and quarantine populations.",
            "paths": [
                "audit_summary.valid_transaction_count",
                "audit_summary.mismatch_count",
                "audit_summary.quarantine_count",
                "audit_summary.quarantine_reason_counts",
                "audit_summary.exception_transaction_count",
                "mismatch_transaction_ids",
                "quarantine_transaction_ids",
            ],
        },
        {
            "point_id": "SP003",
            "weight": 3,
            "goal": "Exact effective-reference decisions and reference-policy controls.",
            "paths": ["effective_reference_panel"],
        },
        {
            "point_id": "SP004",
            "weight": 2,
            "goal": "Exact transaction source, recognition, ledger, and control decisions.",
            "paths": ["transaction_decision_panel"],
        },
        {
            "point_id": "SP005",
            "weight": 1,
            "goal": "Exact normalized volume totals by fuel type.",
            "paths": [
                "normalized_totals.valid_transaction_count",
                "normalized_totals.total_volume_l",
                "normalized_totals.fuel_type_totals[].fuel_type",
                "normalized_totals.fuel_type_totals[].transaction_count",
                "normalized_totals.fuel_type_totals[].volume_l",
            ],
        },
        {
            "point_id": "SP006",
            "weight": 2,
            "goal": "Exact normalized spend totals by fuel type.",
            "paths": [
                "normalized_totals.total_spend_usd",
                "normalized_totals.fuel_type_totals[].spend_usd",
            ],
        },
        {
            "point_id": "SP007",
            "weight": 2,
            "goal": "Exact focus-asset reconciliation results.",
            "paths": ["focus_assets"],
        },
        {
            "point_id": "SP008",
            "weight": 2,
            "goal": "Exact merchant exception ranking.",
            "paths": ["merchant_exception_ranking"],
        },
        {
            "point_id": "SP009",
            "weight": 3,
            "goal": "Exact reconciliation status and operational action.",
            "paths": ["reconciliation_status"],
        },
    ],
    "test_003": [
        {
            "point_id": "SP001",
            "weight": 3,
            "goal": "Exact authoritative source decision and record-level source controls.",
            "paths": [
                "source_decision",
                "edge_case_decisions[].source_choice_code",
                "edge_case_decisions[].source_control_code",
            ],
        },
        {
            "point_id": "SP002",
            "weight": 1,
            "goal": "Exact maintenance integrity issue-class counts.",
            "paths": ["issue_counts"],
        },
        {
            "point_id": "SP003",
            "weight": 3,
            "goal": "Exact overlap duplicate retention and history-route controls.",
            "paths": [
                "duplicate_groups",
                "edge_case_decisions[].selected_snapshot_id",
                "edge_case_decisions[].history_route_code",
            ],
        },
        {
            "point_id": "SP004",
            "weight": 1,
            "goal": "Exact invalid-event population and integrity classifications.",
            "paths": [
                "invalid_event_ids",
                "edge_case_decisions[].event_id",
                "edge_case_decisions[].integrity_class",
                "edge_case_decisions[].primary_issue_code",
            ],
        },
        {
            "point_id": "SP005",
            "weight": 2,
            "goal": "Exact odometer-regression case measurements.",
            "paths": ["regression_cases"],
        },
        {
            "point_id": "SP006",
            "weight": 2,
            "goal": "Exact corrected continuity, Q2 coverage, and distance metrics.",
            "paths": ["corrected_metrics"],
        },
        {
            "point_id": "SP007",
            "weight": 1,
            "goal": "Exact reliable-predecessor, normalized-reading, and history actions.",
            "paths": [
                "edge_case_decisions[].prior_reliable_event_id",
                "edge_case_decisions[].normalized_odometer_km",
                "edge_case_decisions[].history_action",
            ],
        },
        {
            "point_id": "SP008",
            "weight": 1,
            "goal": "Exact highest-risk asset ranking.",
            "paths": ["asset_risk_ranking"],
        },
        {
            "point_id": "SP009",
            "weight": 3,
            "goal": "Exact certification status and operational action.",
            "paths": ["certification_status"],
        },
    ],
    "test_004": [
        {
            "point_id": "SP001",
            "weight": 3,
            "goal": "Exact baseline scope, canonical-owner, contested-case, and readiness counts.",
            "paths": [
                "merge_summary.raw_row_count",
                "merge_summary.canonical_owner_count",
                "merge_summary.merged_duplicate_cluster_count",
                "merge_summary.contested_identifier_case_count",
                "merge_summary.outreach_ready_owner_count",
            ],
        },
        {
            "point_id": "SP002",
            "weight": 1,
            "goal": "Exact quarantined-row count.",
            "paths": ["merge_summary.quarantine_row_count"],
        },
        {
            "point_id": "SP003",
            "weight": 3,
            "goal": "Exact focus-owner memberships, master links, and seed identities.",
            "paths": [
                "focus_owners[].focus_owner_id",
                "focus_owners[].seed_row_id",
                "focus_owners[].member_row_ids",
                "focus_owners[].master_id",
            ],
        },
        {
            "point_id": "SP004",
            "weight": 3,
            "goal": "Exact canonical owner contact and policy-state fields.",
            "paths": [
                "focus_owners[].canonical_name",
                "focus_owners[].canonical_email",
                "focus_owners[].canonical_phone_digits",
                "focus_owners[].canonical_city",
                "focus_owners[].canonical_region_code",
                "focus_owners[].canonical_country_code",
                "focus_owners[].canonical_consent_status",
                "focus_owners[].canonical_record_status",
            ],
        },
        {
            "point_id": "SP005",
            "weight": 1,
            "goal": "Exact focus-owner readiness decisions and routes.",
            "paths": ["focus_owners[].readiness_decision"],
        },
        {
            "point_id": "SP006",
            "weight": 1,
            "goal": "Exact unsafe-identifier and channel-transfer safety adjudications.",
            "paths": ["identifier_case_decisions", "contact_transfer_adjudications"],
        },
        {
            "point_id": "SP007",
            "weight": 2,
            "goal": "Exact field-precedence controls, selected rows, values, and reasons.",
            "paths": ["field_precedence_decisions"],
        },
        {
            "point_id": "SP008",
            "weight": 1,
            "goal": "Exact ordered snapshot-admission replay and stage boundaries.",
            "paths": ["snapshot_admission_replay"],
        },
        {
            "point_id": "SP009",
            "weight": 1,
            "goal": "Exact unsafe-identity graph impacts and household remediation portfolio.",
            "paths": [
                "unsafe_identity_rule_impacts",
                "unsafe_household_outreach_counterfactual",
            ],
        },
        {
            "point_id": "SP010",
            "weight": 1,
            "goal": "Exact source-removal restoration portfolio and recovered-owner population.",
            "paths": ["source_removal_stability_audit"],
        },
    ],
    "test_005": [
        {
            "point_id": "SP001",
            "weight": 3,
            "goal": "Exact source-scope accounting and duplicate-charge reconstruction.",
            "paths": ["audit_summary", "duplicate_groups"],
        },
        {
            "point_id": "SP002",
            "weight": 2,
            "goal": "Exact alias-reference policy and eligibility decisions.",
            "paths": ["alias_reference_cases"],
        },
        {
            "point_id": "SP003",
            "weight": 3,
            "goal": "Exact charge-level source, recognition, conversion, and accrual decisions.",
            "paths": [
                "charge_decisions[].charge_id",
                "charge_decisions[].retained_snapshot_id",
                "charge_decisions[].source_control_code",
                "charge_decisions[].source_treatment",
                "charge_decisions[].applicable_alias_ids",
                "charge_decisions[].decisive_alias_ids",
                "charge_decisions[].recognition_outcome",
                "charge_decisions[].recognized_service_class",
                "charge_decisions[].class_relation",
                "charge_decisions[].accrual_disposition",
                "charge_decisions[].quarantine_reason",
                "charge_decisions[].weight_eligible",
                "charge_decisions[].distance_eligible",
                "charge_decisions[].selected_fx_status",
                "charge_decisions[].selected_usd_per_unit",
                "charge_decisions[].converted_weight_kg",
                "charge_decisions[].converted_distance_km",
                "charge_decisions[].converted_amount_usd",
                "charge_decisions[].included_in_totals",
                "charge_decisions[].included_spend_usd",
            ],
        },
        {
            "point_id": "SP004",
            "weight": 2,
            "goal": "Exact charge and invoice-route ledger controls.",
            "paths": [
                "charge_decisions[].ledger_disposition_code",
                "invoice_route_ledger_controls",
            ],
        },
        {
            "point_id": "SP005",
            "weight": 3,
            "goal": "Exact mismatch and quarantine charge populations.",
            "paths": ["class_mismatch_charge_ids", "quarantine_charge_ids"],
        },
        {
            "point_id": "SP006",
            "weight": 1,
            "goal": "Exact normalized totals and focus-lane reconciliation.",
            "paths": ["normalized_totals", "focus_lanes"],
        },
        {
            "point_id": "SP007",
            "weight": 3,
            "goal": "Exact carrier exposure ranking.",
            "paths": ["carrier_ranking"],
        },
        {
            "point_id": "SP008",
            "weight": 3,
            "goal": "Exact integrated close-evidence reconstruction and close routing.",
            "paths": [
                "integrated_close_evidence_release_assessment",
                "close_status",
            ],
        },
        {
            "point_id": "SP009",
            "weight": 3,
            "goal": "Exact unsafe-union graph containment certificates.",
            "paths": ["unsafe_aggregation_containment_plan"],
        },
        {
            "point_id": "SP010",
            "weight": 2,
            "goal": "Exact certified-versus-provisional FX counterfactual exposure.",
            "paths": ["fx_certification_impact"],
        },
    ],
}


def same_scalar_type(candidate: Any, gold: Any) -> bool:
    if isinstance(gold, bool):
        return isinstance(candidate, bool)
    if isinstance(gold, int) and not isinstance(gold, bool):
        return isinstance(candidate, int) and not isinstance(candidate, bool)
    if isinstance(gold, float):
        return (
            isinstance(candidate, (int, float))
            and not isinstance(candidate, bool)
            and math.isfinite(float(candidate))
        )
    if gold is None:
        return candidate is None
    return isinstance(candidate, type(gold))


def validate_structure(candidate: Any, gold: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(gold, dict):
        if not isinstance(candidate, dict):
            return [f"{path}: expected object"]
        missing = sorted(set(gold) - set(candidate))
        extra = sorted(set(candidate) - set(gold))
        errors.extend(f"{path}: missing required key {key}" for key in missing)
        errors.extend(f"{path}: unexpected key {key}" for key in extra)
        for key in sorted(set(gold) & set(candidate)):
            errors.extend(validate_structure(candidate[key], gold[key], f"{path}.{key}"))
        return errors

    if isinstance(gold, list):
        if not isinstance(candidate, list):
            return [f"{path}: expected array"]
        if not gold:
            return errors
        for index, item in enumerate(candidate):
            exemplar = gold[index] if index < len(gold) else gold[-1]
            errors.extend(validate_structure(item, exemplar, f"{path}[{index}]"))
        return errors

    if not same_scalar_type(candidate, gold):
        errors.append(f"{path}: incompatible scalar type")
    return errors


def exact_equal(candidate: Any, gold: Any) -> bool:
    if isinstance(gold, bool):
        return isinstance(candidate, bool) and candidate == gold
    if isinstance(gold, int) and not isinstance(gold, bool):
        return (
            isinstance(candidate, int)
            and not isinstance(candidate, bool)
            and candidate == gold
        )
    if isinstance(gold, float):
        return (
            isinstance(candidate, (int, float))
            and not isinstance(candidate, bool)
            and math.isfinite(float(candidate))
            and abs(float(candidate) - gold) <= 0.00005
        )
    if gold is None or isinstance(gold, str):
        return candidate == gold
    if isinstance(gold, list):
        return (
            isinstance(candidate, list)
            and len(candidate) == len(gold)
            and all(exact_equal(left, right) for left, right in zip(candidate, gold))
        )
    if isinstance(gold, dict):
        return (
            isinstance(candidate, dict)
            and candidate.keys() == gold.keys()
            and all(exact_equal(candidate[key], value) for key, value in gold.items())
        )
    return candidate == gold


def parse_path(path: str) -> list[str]:
    parts: list[str] = []
    for component in path.split("."):
        if component.endswith("[]"):
            parts.extend([component[:-2], "*"])
        else:
            parts.append(component)
    return parts


def extract(document: Any, parts: list[str]) -> Any:
    if not parts:
        return document
    component, *remaining = parts
    if component == "*":
        if not isinstance(document, list):
            raise TypeError("wildcard requires an array")
        return [extract(item, remaining) for item in document]
    if not isinstance(document, dict) or component not in document:
        raise KeyError(component)
    return extract(document[component], remaining)


def infer_task_id(gold_path: Path) -> str | None:
    parts = gold_path.resolve().parts
    if "test_tasks" not in parts:
        return None
    index = parts.index("test_tasks")
    if index + 1 >= len(parts):
        return None
    return f"test_{parts[index + 1]}"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: whole_point_eval.py PREDICTION GOLD", file=sys.stderr)
        return 2

    prediction_path = Path(sys.argv[1])
    gold_path = Path(sys.argv[2])
    task_id = infer_task_id(gold_path)
    specs = POINT_SPECS.get(task_id or "")
    if specs is None:
        print(json.dumps({"score": 0.0, "evaluator_error": "unknown test task"}))
        return 1

    parse_error: str | None = None
    try:
        prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
    except Exception as exc:
        prediction = None
        parse_error = str(exc)

    try:
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"score": 0.0, "evaluator_error": f"gold: {exc}"}))
        return 1

    structure_errors = (
        [] if parse_error is not None else validate_structure(prediction, gold)
    )
    structure_valid = parse_error is None and not structure_errors
    total_weight = sum(int(spec["weight"]) for spec in specs)
    points: list[dict[str, Any]] = []

    for spec in specs:
        failed_paths: list[str] = []
        if structure_valid:
            for path in spec["paths"]:
                try:
                    candidate_value = extract(prediction, parse_path(path))
                    gold_value = extract(gold, parse_path(path))
                    if not exact_equal(candidate_value, gold_value):
                        failed_paths.append(path)
                except (KeyError, TypeError, IndexError):
                    failed_paths.append(path)
        else:
            failed_paths = list(spec["paths"])

        passed = structure_valid and not failed_paths
        raw_weight = int(spec["weight"])
        assigned_score = raw_weight / total_weight
        points.append(
            {
                "point_id": spec["point_id"],
                "goal": spec["goal"],
                "raw_weight": raw_weight,
                "assigned_score": assigned_score,
                "passed": passed,
                "earned_score": assigned_score if passed else 0.0,
                "details": {
                    "evaluation_policy": "all declared business-result paths must match",
                    "declared_paths": spec["paths"],
                    "failed_paths": failed_paths,
                },
            }
        )

    score = sum(point["earned_score"] for point in points)
    print(
        json.dumps(
            {
                "score": score,
                "correct": abs(score - 1.0) <= 1e-12,
                "valid_json": parse_error is None,
                "structure_valid": structure_valid,
                "structure_errors": structure_errors[:100],
                "parse_error": parse_error,
                "points": points,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
