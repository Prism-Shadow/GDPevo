#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ANSWER_PATH = SCRIPT_DIR.parent / "output" / "answer.json"

CATEGORY_KEYS = ["fuel", "maintenance", "freight", "accessorial", "claim", "tax_fee", "unknown"]
REASON_KEYS = [
    "duplicate",
    "invalid_amount",
    "invalid_unit",
    "missing_contact_channel",
    "suppressed_contact",
    "ambiguous_alias",
    "superseded",
    "source_conflict",
]


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def cents(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None


def money_object(obj, keys):
    if not isinstance(obj, dict):
        return None
    return {key: cents(obj.get(key)) for key in keys}


def int_object(obj, keys):
    if not isinstance(obj, dict):
        return None
    normalized = {}
    for key in keys:
        value = obj.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        normalized[key] = value
    return normalized


def sample_by_id(answer):
    sample = answer.get("canonical_charge_sample")
    if not isinstance(sample, list):
        return {}
    return {row.get("charge_id"): row for row in sample if isinstance(row, dict)}


def normalize_sample_row(row):
    if not isinstance(row, dict):
        return None
    return {
        "charge_id": row.get("charge_id"),
        "business_key": row.get("business_key"),
        "vendor": row.get("vendor"),
        "canonical_category": row.get("canonical_category"),
        "adjusted_amount_usd": cents(row.get("adjusted_amount_usd")),
        "review_reasons": row.get("review_reasons"),
    }


def main() -> int:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ANSWER_PATH
    try:
        expected = load_json(ANSWER_PATH)
        actual = load_json(prediction_path)
    except Exception as exc:
        print(json.dumps({"score": 0, "max_score": 17, "normalized_score": 0.0, "error": str(exc)}, indent=2))
        return 0

    expected_vendor = dict(expected["top_vendor_by_adjusted_spend"])
    actual_vendor = actual.get("top_vendor_by_adjusted_spend")
    if isinstance(actual_vendor, dict):
        actual_vendor = dict(actual_vendor)
        actual_vendor["adjusted_spend_usd"] = cents(actual_vendor.get("adjusted_spend_usd"))
    expected_vendor["adjusted_spend_usd"] = cents(expected_vendor["adjusted_spend_usd"])

    expected_sample = sample_by_id(expected)
    actual_sample = sample_by_id(actual)
    seeded_ids = ["FC_W_001", "FC_W_002", "FC_W_004", "FC_W_005"]

    points = [
        {
            "id": "SP001_scope_and_effective_count",
            "weight": 2,
            "passed": actual.get("scope") == expected["scope"]
            and actual.get("effective_charge_count") == expected["effective_charge_count"],
        },
        {
            "id": "SP002_invalid_and_superseded_ids",
            "weight": 2,
            "passed": actual.get("invalid_charge_ids") == expected["invalid_charge_ids"]
            and actual.get("superseded_charge_ids") == expected["superseded_charge_ids"],
        },
        {
            "id": "SP003_category_counts",
            "weight": 2,
            "passed": int_object(actual.get("category_counts"), CATEGORY_KEYS) == expected["category_counts"],
        },
        {
            "id": "SP004_spend_by_category_usd",
            "weight": 3,
            "passed": money_object(actual.get("spend_by_category_usd"), CATEGORY_KEYS)
            == money_object(expected["spend_by_category_usd"], CATEGORY_KEYS),
        },
        {
            "id": "SP005_top_vendor_by_adjusted_spend",
            "weight": 2,
            "passed": actual_vendor == expected_vendor,
        },
        {
            "id": "SP006_review_reason_counts",
            "weight": 2,
            "passed": int_object(actual.get("review_reason_counts"), REASON_KEYS) == expected["review_reason_counts"],
        },
        {
            "id": "SP007_seeded_canonical_charge_sample",
            "weight": 3,
            "passed": all(
                normalize_sample_row(actual_sample.get(charge_id)) == normalize_sample_row(expected_sample.get(charge_id))
                for charge_id in seeded_ids
            ),
        },
        {
            "id": "SP008_ambiguous_charge_sample",
            "weight": 1,
            "passed": normalize_sample_row(actual_sample.get("FC_BG_0000"))
            == normalize_sample_row(expected_sample.get("FC_BG_0000")),
        },
    ]

    score = sum(point["weight"] for point in points if point["passed"])
    max_score = sum(point["weight"] for point in points)
    result = {
        "score": score,
        "max_score": max_score,
        "normalized_score": round(score / max_score, 6),
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
