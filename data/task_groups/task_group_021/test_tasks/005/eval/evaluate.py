#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
GOLD_PATH = TASK_DIR / "output" / "answer.json"

CATEGORY_KEYS = ["freight", "accessorial", "tax_fee", "claim"]
UNIT_KEYS = ["kg", "lb", "mile", "shipment", "claim"]
ISSUE_KEYS = [
    "invalid_negative_amount",
    "missing_amount",
    "invalid_unit",
    "invalid_currency",
    "void_record",
    "superseded_record",
    "amended_record",
    "duplicate_business_key",
    "non_usd_currency",
    "advisory_note",
]

POINTS = [
    {
        "id": "SP001",
        "goal": "Correct target identifiers and effective claim-event count.",
        "weight": 1,
        "fields": ["batch_id", "wave_id", "effective_claim_count"],
    },
    {
        "id": "SP002",
        "goal": "Correct invalid event IDs and their controlled issue types.",
        "weight": 1,
        "fields": ["invalid_event_ids", "invalid_event_issue_types"],
    },
    {
        "id": "SP003",
        "goal": "Correct lifecycle reconstruction audit for duplicate, void/superseded, and amendment handling.",
        "weight": 2,
        "fields": [
            "duplicate_business_key_count",
            "superseded_or_void_event_ids",
            "amended_event_ids_used",
            "decision_audit",
        ],
    },
    {
        "id": "SP004",
        "goal": "Correct total corrected claims batch cost in USD cents.",
        "weight": 1,
        "fields": ["corrected_claim_total_usd"],
    },
    {
        "id": "SP005",
        "goal": "Correct corrected USD totals and effective counts for each claim category.",
        "weight": 2,
        "fields": ["totals_by_claim_category_usd", "claim_category_counts"],
    },
    {
        "id": "SP006",
        "goal": "Correct top claim lane by corrected cost and lane amount.",
        "weight": 1,
        "fields": ["top_claim_lane_by_cost"],
    },
    {
        "id": "SP007",
        "goal": "Correct effective source-unit counts after exclusions.",
        "weight": 1,
        "fields": ["unit_count_by_source_unit"],
    },
    {
        "id": "SP008",
        "goal": "Correct raw invalid-unit issue taxonomy count.",
        "weight": 3,
        "fields": ["issue_type_counts.invalid_unit"],
    },
    {
        "id": "SP009",
        "goal": "Correct non-USD issue-count scope.",
        "weight": 1,
        "fields": ["issue_type_counts.non_usd_currency"],
    },
    {
        "id": "SP010",
        "goal": "Correct remaining controlled issue-type counts.",
        "weight": 1,
        "fields": [
            "issue_type_counts.invalid_negative_amount",
            "issue_type_counts.missing_amount",
            "issue_type_counts.invalid_currency",
            "issue_type_counts.void_record",
            "issue_type_counts.superseded_record",
            "issue_type_counts.amended_record",
            "issue_type_counts.duplicate_business_key",
            "issue_type_counts.advisory_note",
        ],
    },
]

MONEY_FIELDS = {
    ("corrected_claim_total_usd",),
    ("totals_by_claim_category_usd", "freight"),
    ("totals_by_claim_category_usd", "accessorial"),
    ("totals_by_claim_category_usd", "tax_fee"),
    ("totals_by_claim_category_usd", "claim"),
    ("top_claim_lane_by_cost", "amount_usd"),
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cents(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize_int_object(value, keys):
    if not isinstance(value, dict):
        return None
    normalized = {}
    for key in keys:
        item = value.get(key)
        if isinstance(item, bool) or not isinstance(item, int):
            return None
        normalized[key] = item
    return normalized


def normalize_value(value, path=()):
    if path in MONEY_FIELDS:
        return cents(value)
    if path == ("claim_category_counts",):
        return normalize_int_object(value, CATEGORY_KEYS)
    if path == ("unit_count_by_source_unit",):
        return normalize_int_object(value, UNIT_KEYS)
    if path == ("issue_type_counts",):
        return normalize_int_object(value, ISSUE_KEYS)
    if isinstance(value, dict):
        return {key: normalize_value(item, path + (key,)) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_value(item, path + ("[]",)) for item in value]
    return value


def get_path(obj, field):
    value = obj
    for key in field.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def project(obj, fields):
    projected = {}
    for field in fields:
        path = tuple(field.split("."))
        projected[field] = normalize_value(get_path(obj, field), path)
    return projected


def main() -> int:
    prediction_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    prediction_path = Path(prediction_arg) if prediction_arg else GOLD_PATH
    if not prediction_path.is_absolute():
        prediction_path = Path.cwd() / prediction_path

    gold = load_json(GOLD_PATH)
    try:
        pred = load_json(prediction_path)
    except Exception as exc:
        total_weight = sum(point["weight"] for point in POINTS)
        print(json.dumps({
            "score": 0,
            "max_score": total_weight,
            "normalized_score": 0.0,
            "error": f"Could not parse prediction JSON: {exc}",
            "points": [],
        }, indent=2))
        return 0

    scored = []
    score = 0
    for point in POINTS:
        expected = project(gold, point["fields"])
        actual = project(pred, point["fields"])
        passed = actual == expected
        if passed:
            score += point["weight"]
        scored.append({
            "id": point["id"],
            "goal": point["goal"],
            "weight": point["weight"],
            "passed": passed,
            "expected": expected,
            "actual": actual,
        })

    total_weight = sum(point["weight"] for point in POINTS)
    print(json.dumps({
        "score": score,
        "max_score": total_weight,
        "normalized_score": round(score / total_weight, 6),
        "points": scored,
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
