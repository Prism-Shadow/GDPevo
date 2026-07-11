#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


FUEL_KEYS = ["diesel", "unleaded", "premium_unleaded", "electric", "hybrid", "unknown"]
ALIAS_KEYS = [
    "priority_overlap_matches",
    "generic_unleaded_traps",
    "ambiguous_unknown_matches",
    "unmapped_descriptions",
]
SOURCE_DELTA_COUNT_KEYS = [
    "api_only_current_records",
    "csv_only_legacy_records",
    "csv_stale_records",
    "disagreement_transaction_keys",
    "csv_records_excluded_from_operational_totals",
]


POINTS = [
    {
        "id": "SP1",
        "goal": "Correct audit scope, effective purchase count, lifecycle evidence, and source-delta counts.",
        "weight": 2,
        "fields": ["region", "period", "purchase_count_evaluated"],
    },
    {
        "id": "SP2",
        "goal": "Correct gallons by canonical fuel class and source-exclusion evidence.",
        "weight": 3,
        "fields": ["gallons_by_canonical_fuel"],
    },
    {
        "id": "SP3",
        "goal": "Correct mismatch purchase ID set and source-exclusion evidence.",
        "weight": 3,
        "fields": ["mismatch_purchase_ids"],
    },
    {
        "id": "SP4",
        "goal": "Correct exception purchase IDs for effective-record and vehicle-exception handling.",
        "weight": 3,
        "fields": ["exception_purchase_ids"],
    },
    {
        "id": "SP5",
        "goal": "Correct vehicle review queue with expected and observed fuel classes.",
        "weight": 3,
        "fields": ["vehicle_review_queue"],
    },
    {
        "id": "SP6",
        "goal": "Correct vendor mismatch counts.",
        "weight": 2,
        "fields": ["vendor_mismatch_counts"],
    },
    {
        "id": "SP7",
        "goal": "Correct alias issue counts for priority overlaps, traps, and unknowns.",
        "weight": 3,
        "fields": ["alias_issue_counts"],
    },
    {
        "id": "SP8",
        "goal": "Correct alias-resolution trace for nontrivial effective purchases.",
        "weight": 3,
        "fields": ["decision_audit"],
    },
    {
        "id": "SP9",
        "goal": "Correct API-vs-CSV source delta purchase ID sets.",
        "weight": 3,
        "fields": ["source_delta_audit"],
    },
    {
        "id": "SP10",
        "goal": "Correct transaction-level reconciliation and operations load decisions for source disagreements.",
        "weight": 3,
        "fields": ["transaction_reconciliation", "operations_load_decision_audit"],
    },
]


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def round_gallons(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return value


def normalize_gallons(obj):
    if not isinstance(obj, dict):
        return obj
    return {key: round_gallons(obj.get(key)) for key in FUEL_KEYS}


def normalize_int_object(obj, keys):
    if not isinstance(obj, dict):
        return obj
    normalized = {}
    for key in keys:
        value = obj.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            normalized[key] = value
        else:
            normalized[key] = value
    return normalized


def normalize_queue(value):
    if not isinstance(value, list):
        return value
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        normalized.append(
            {
                "vehicle_id": item.get("vehicle_id"),
                "expected_fuel": item.get("expected_fuel"),
                "observed_fuel": item.get("observed_fuel"),
                "purchase_ids": item.get("purchase_ids"),
            }
        )
    return normalized


def normalize_decision_audit(value):
    if not isinstance(value, dict):
        return value
    return {
        "alias_priority_purchase_ids": sorted(value.get("alias_priority_purchase_ids", [])),
        "generic_unleaded_trap_purchase_ids": sorted(value.get("generic_unleaded_trap_purchase_ids", [])),
        "unknown_alias_purchase_ids": sorted(value.get("unknown_alias_purchase_ids", [])),
        "unmapped_description_purchase_ids": sorted(value.get("unmapped_description_purchase_ids", [])),
        "void_purchase_ids": sorted(value.get("void_purchase_ids", [])),
        "amended_purchase_ids": sorted(value.get("amended_purchase_ids", [])),
        "superseded_purchase_ids": sorted(value.get("superseded_purchase_ids", [])),
        "vehicle_exception_purchase_ids": sorted(value.get("vehicle_exception_purchase_ids", [])),
        "zero_gallon_purchase_ids": sorted(value.get("zero_gallon_purchase_ids", [])),
        "alias_resolution_trace": normalize_alias_trace(value.get("alias_resolution_trace")),
    }


def normalize_source_delta(value):
    if not isinstance(value, dict):
        return value
    return {
        "api_only_current_purchase_ids": sorted(value.get("api_only_current_purchase_ids", [])),
        "csv_only_legacy_purchase_ids": sorted(value.get("csv_only_legacy_purchase_ids", [])),
        "csv_stale_purchase_ids": sorted(value.get("csv_stale_purchase_ids", [])),
        "source_disagreement_transaction_keys": sorted(value.get("source_disagreement_transaction_keys", [])),
        "csv_records_excluded_from_operational_totals": sorted(
            value.get("csv_records_excluded_from_operational_totals", [])
        ),
        "source_delta_counts": normalize_int_object(value.get("source_delta_counts"), SOURCE_DELTA_COUNT_KEYS),
    }


def normalize_transaction_reconciliation(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return value
        rows.append(
            {
                "transaction_key": str(item.get("transaction_key", "")).strip(),
                "current_api_purchase_ids": sorted(item.get("current_api_purchase_ids", [])),
                "excluded_purchase_ids": sorted(item.get("excluded_purchase_ids", [])),
                "csv_export_purchase_ids": sorted(item.get("csv_export_purchase_ids", [])),
                "reconciliation_status": str(item.get("reconciliation_status", "")).strip(),
            }
        )
    return sorted(rows, key=lambda row: row["transaction_key"])


def normalize_operations_load_decisions(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return value
        rows.append(
            {
                "purchase_id": str(item.get("purchase_id", "")).strip(),
                "source_action": str(item.get("source_action", "")).strip(),
                "ops_action": str(item.get("ops_action", "")).strip(),
                "owner": str(item.get("owner", "")).strip(),
                "metric_effect": str(item.get("metric_effect", "")).strip(),
                "decision_reasons": sorted(str(reason).strip() for reason in item.get("decision_reasons", [])),
            }
        )
    return sorted(rows, key=lambda row: row["purchase_id"])


def normalize_alias_trace(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return value
        rows.append(
            {
                "purchase_id": str(item.get("purchase_id", "")).strip(),
                "selected_alias": str(item.get("selected_alias", "")).strip().lower(),
                "canonical_fuel": str(item.get("canonical_fuel", "")).strip(),
                "matched_aliases": sorted(str(alias).strip().lower() for alias in item.get("matched_aliases", [])),
                "audit_reasons": sorted(str(reason).strip() for reason in item.get("audit_reasons", [])),
            }
        )
    return sorted(rows, key=lambda row: row["purchase_id"])


def normalize_field(field, value):
    if field == "gallons_by_canonical_fuel":
        return normalize_gallons(value)
    if field == "alias_issue_counts":
        return normalize_int_object(value, ALIAS_KEYS)
    if field == "vehicle_review_queue":
        return normalize_queue(value)
    if field == "decision_audit":
        return normalize_decision_audit(value)
    if field == "source_delta_audit":
        return normalize_source_delta(value)
    if field == "transaction_reconciliation":
        return normalize_transaction_reconciliation(value)
    if field == "operations_load_decision_audit":
        return normalize_operations_load_decisions(value)
    return value


def point_matches(point, expected, prediction):
    expected_audit = normalize_decision_audit(expected.get("decision_audit"))
    predicted_audit = normalize_decision_audit(prediction.get("decision_audit"))
    expected_delta = normalize_source_delta(expected.get("source_delta_audit"))
    predicted_delta = normalize_source_delta(prediction.get("source_delta_audit"))
    expected_ops = normalize_operations_load_decisions(expected.get("operations_load_decision_audit"))
    predicted_ops = normalize_operations_load_decisions(prediction.get("operations_load_decision_audit"))
    for field in point["fields"]:
        if normalize_field(field, prediction.get(field)) != normalize_field(field, expected.get(field)):
            return False
    if point["id"] == "SP1":
        return (
            predicted_audit
            and expected_audit
            and predicted_delta
            and expected_delta
            and predicted_audit.get("void_purchase_ids") == expected_audit.get("void_purchase_ids")
            and predicted_audit.get("amended_purchase_ids") == expected_audit.get("amended_purchase_ids")
            and predicted_audit.get("superseded_purchase_ids") == expected_audit.get("superseded_purchase_ids")
            and predicted_delta.get("source_delta_counts") == expected_delta.get("source_delta_counts")
        )
    if point["id"] == "SP2":
        return (
            predicted_audit
            and expected_audit
            and predicted_delta
            and expected_delta
            and predicted_audit == expected_audit
            and predicted_delta.get("csv_records_excluded_from_operational_totals")
            == expected_delta.get("csv_records_excluded_from_operational_totals")
        )
    if point["id"] == "SP3":
        return (
            predicted_audit
            and expected_audit
            and predicted_delta
            and expected_delta
            and predicted_ops
            and expected_ops
            and predicted_audit == expected_audit
            and predicted_delta.get("csv_records_excluded_from_operational_totals")
            == expected_delta.get("csv_records_excluded_from_operational_totals")
            and predicted_ops == expected_ops
        )
    if point["id"] in {"SP7", "SP8"}:
        return predicted_audit and expected_audit and predicted_audit == expected_audit
    if point["id"] == "SP4":
        return (
            predicted_audit
            and expected_audit
            and predicted_ops
            and expected_ops
            and predicted_audit.get("void_purchase_ids") == expected_audit.get("void_purchase_ids")
            and predicted_audit.get("superseded_purchase_ids") == expected_audit.get("superseded_purchase_ids")
            and predicted_audit.get("vehicle_exception_purchase_ids")
            == expected_audit.get("vehicle_exception_purchase_ids")
            and predicted_ops == expected_ops
        )
    if point["id"] == "SP5":
        return predicted_audit and expected_audit and predicted_ops and expected_ops and predicted_audit == expected_audit and predicted_ops == expected_ops
    if point["id"] == "SP9":
        return predicted_delta and expected_delta and predicted_ops and expected_ops and predicted_delta == expected_delta and predicted_ops == expected_ops
    return True


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    expected_path = script_dir.parent / "output" / "answer.json"
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else expected_path

    try:
        expected = load_json(expected_path)
        prediction = load_json(prediction_path)
    except Exception as exc:
        result = {
            "score": 0,
            "max_score": sum(point["weight"] for point in POINTS),
            "normalized_score": 0.0,
            "error": f"Could not load JSON: {exc}",
            "points": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    max_score = sum(point["weight"] for point in POINTS)
    earned = 0
    point_results = []
    for point in POINTS:
        matched = bool(point_matches(point, expected, prediction))
        if matched:
            earned += point["weight"]
        point_results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "earned": point["weight"] if matched else 0,
                "matched": matched,
            }
        )

    result = {
        "score": earned,
        "max_score": max_score,
        "normalized_score": round(earned / max_score, 6),
        "points": point_results,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
