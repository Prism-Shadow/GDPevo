#!/usr/bin/env python3
import json
import sys
from pathlib import Path


SCORING_POINTS = [
    {
        "id": "SP001_lineage",
        "weight": 2,
        "top_fields": ["task_id"],
        "lineage_fields": [
            "as_of_date",
            "target_quarter",
            "prior_quarter",
            "prior_view_record_quarter",
            "policy_id",
            "mapping_policy_id",
        ],
    },
    {
        "id": "SP002_prior_view_and_signal_lineage",
        "weight": 3,
        "rows": "ALL",
        "fields": ["prior_view", "current_signal_score"],
    },
    {
        "id": "SP003_core_equity_views",
        "weight": 2,
        "rows": ["U.S. Large Cap", "U.S. Small Cap", "Europe", "Japan"],
        "fields": ["asset_class", "view", "change", "conviction"],
    },
    {
        "id": "SP004_diversifier_equity_views",
        "weight": 2,
        "rows": ["Emerging Markets", "India", "Latin America"],
        "fields": ["asset_class", "view", "change", "conviction"],
    },
    {
        "id": "SP005_fixed_income_views",
        "weight": 2,
        "rows": [
            "U.S. Treasuries",
            "German Bunds",
            "Corporate Investment Grade",
            "Corporate High Yield",
        ],
        "fields": ["asset_class", "view", "change", "conviction"],
    },
    {
        "id": "SP006_currency_active_views",
        "weight": 2,
        "rows": ["USD", "EUR", "JPY", "CHF"],
        "fields": ["asset_class", "view", "change", "conviction"],
    },
    {
        "id": "SP007_controlled_rationale_codes",
        "weight": 3,
        "rows": "ALL",
        "fields": ["rationale_code"],
    },
    {
        "id": "SP008_currency_overlay",
        "weight": 3,
        "overlay_fields": ["base_currency", "policy_action"],
        "decision_fields": ["prior_view", "active_view", "overlay_action", "rationale_code"],
    },
    {
        "id": "SP009_cross_asset_judgments",
        "weight": 2,
        "judgment_fields": ["equity_relative_value", "rates_credit_mix", "currency_overlay_bias"],
    },
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_rows(answer):
    rows = answer.get("allocation_views", [])
    if not isinstance(rows, list):
        return {}
    normalized = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("opportunity_set"), str):
            normalized[row["opportunity_set"]] = row
    return normalized


def normalize_overlay_decisions(answer):
    overlay = answer.get("currency_overlay", {})
    rows = overlay.get("decisions", []) if isinstance(overlay, dict) else []
    if not isinstance(rows, list):
        return {}
    normalized = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("currency"), str):
            normalized[row["currency"]] = row
    return normalized


def values_match(expected, predicted, field):
    if field == "current_signal_score":
        try:
            return round(float(predicted), 3) == round(float(expected), 3)
        except (TypeError, ValueError):
            return False
    return predicted == expected


def lineage_match(expected, predicted, top_fields, lineage_fields):
    mismatches = []
    for field in top_fields:
        if predicted.get(field) != expected.get(field):
            mismatches.append({"field": field, "expected": expected.get(field), "predicted": predicted.get(field)})

    expected_lineage = expected.get("lineage", {})
    predicted_lineage = predicted.get("lineage", {})
    if not isinstance(predicted_lineage, dict):
        return False, [{"field": "lineage", "expected": expected_lineage, "predicted": predicted_lineage}]

    for field in lineage_fields:
        if predicted_lineage.get(field) != expected_lineage.get(field):
            mismatches.append(
                {
                    "field": f"lineage.{field}",
                    "expected": expected_lineage.get(field),
                    "predicted": predicted_lineage.get(field),
                }
            )
    return len(mismatches) == 0, mismatches


def row_match(expected_rows, predicted_rows, row_ids, fields):
    mismatches = []
    for row_id in row_ids:
        exp = expected_rows.get(row_id)
        pred = predicted_rows.get(row_id)
        if pred is None:
            mismatches.append({"opportunity_set": row_id, "missing": True})
            continue
        for field in fields:
            if not values_match(exp.get(field), pred.get(field), field):
                mismatches.append(
                    {
                        "opportunity_set": row_id,
                        "field": field,
                        "expected": exp.get(field),
                        "predicted": pred.get(field),
                    }
                )
    return len(mismatches) == 0, mismatches


def overlay_match(expected, predicted, overlay_fields, decision_fields):
    expected_overlay = expected.get("currency_overlay", {})
    predicted_overlay = predicted.get("currency_overlay", {})
    mismatches = []
    if not isinstance(predicted_overlay, dict):
        return False, [{"field": "currency_overlay", "expected": expected_overlay, "predicted": predicted_overlay}]

    for field in overlay_fields:
        if predicted_overlay.get(field) != expected_overlay.get(field):
            mismatches.append(
                {
                    "field": f"currency_overlay.{field}",
                    "expected": expected_overlay.get(field),
                    "predicted": predicted_overlay.get(field),
                }
            )

    expected_decisions = normalize_overlay_decisions(expected)
    predicted_decisions = normalize_overlay_decisions(predicted)
    for currency in ["USD", "EUR", "JPY", "CHF"]:
        exp = expected_decisions.get(currency)
        pred = predicted_decisions.get(currency)
        if pred is None:
            mismatches.append({"currency": currency, "missing": True})
            continue
        for field in decision_fields:
            if pred.get(field) != exp.get(field):
                mismatches.append(
                    {
                        "currency": currency,
                        "field": field,
                        "expected": exp.get(field),
                        "predicted": pred.get(field),
                    }
                )
    return len(mismatches) == 0, mismatches


def judgment_match(expected, predicted, fields):
    expected_judgments = expected.get("cross_asset_judgments", {})
    predicted_judgments = predicted.get("cross_asset_judgments", {})
    if not isinstance(predicted_judgments, dict):
        return False, [
            {
                "field": "cross_asset_judgments",
                "expected": expected_judgments,
                "predicted": predicted_judgments,
            }
        ]

    mismatches = []
    for field in fields:
        if predicted_judgments.get(field) != expected_judgments.get(field):
            mismatches.append(
                {
                    "field": f"cross_asset_judgments.{field}",
                    "expected": expected_judgments.get(field),
                    "predicted": predicted_judgments.get(field),
                }
            )
    return len(mismatches) == 0, mismatches


def evaluate(prediction_path):
    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    expected = load_json(answer_path)
    predicted = load_json(prediction_path)
    expected_rows = normalize_rows(expected)
    predicted_rows = normalize_rows(predicted)
    all_row_ids = [row["opportunity_set"] for row in expected["allocation_views"]]

    details = []
    raw_score = 0
    max_score = sum(point["weight"] for point in SCORING_POINTS)

    for point in SCORING_POINTS:
        if "lineage_fields" in point:
            matched, mismatches = lineage_match(
                expected,
                predicted,
                point["top_fields"],
                point["lineage_fields"],
            )
        elif "rows" in point:
            row_ids = all_row_ids if point["rows"] == "ALL" else point["rows"]
            matched, mismatches = row_match(expected_rows, predicted_rows, row_ids, point["fields"])
        elif "overlay_fields" in point:
            matched, mismatches = overlay_match(
                expected,
                predicted,
                point["overlay_fields"],
                point["decision_fields"],
            )
        else:
            matched, mismatches = judgment_match(expected, predicted, point["judgment_fields"])

        earned = point["weight"] if matched else 0
        raw_score += earned
        details.append(
            {
                "id": point["id"],
                "weight": point["weight"],
                "earned": earned,
                "matched": matched,
                "mismatches": mismatches,
            }
        )

    return {
        "score": raw_score,
        "max_score": max_score,
        "normalized_score": round(raw_score / max_score, 6),
        "details": details,
    }


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python eval.py <prediction_json_path>"}, indent=2))
        sys.exit(2)
    try:
        result = evaluate(sys.argv[1])
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "score": 0,
                    "max_score": sum(p["weight"] for p in SCORING_POINTS),
                    "normalized_score": 0.0,
                },
                indent=2,
            )
        )
        sys.exit(1)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
