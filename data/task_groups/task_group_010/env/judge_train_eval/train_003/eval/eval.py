#!/usr/bin/env python3
import json
import sys
from pathlib import Path


SCORING_POINTS = [
    {
        "id": "SP001_lineage",
        "weight": 1,
        "fields": ["task_id", "as_of_date", "target_quarter", "prior_quarter", "policy_id"],
    },
    {
        "id": "SP002_equity_core_views",
        "weight": 3,
        "rows": ["Europe", "Japan", "Emerging Markets"],
        "fields": ["view"],
    },
    {
        "id": "SP003_diversifier_views",
        "weight": 3,
        "rows": ["India", "Latin America"],
        "fields": ["view"],
    },
    {
        "id": "SP004_rates_credit_currency_views",
        "weight": 3,
        "rows": ["U.S. Treasuries", "Corporate High Yield", "EUR"],
        "fields": ["view"],
    },
    {
        "id": "SP005_all_changes",
        "weight": 2,
        "rows": "ALL",
        "fields": ["change"],
    },
    {
        "id": "SP006_all_convictions",
        "weight": 2,
        "rows": "ALL",
        "fields": ["conviction"],
    },
    {
        "id": "SP007_all_rationale_codes",
        "weight": 2,
        "rows": "ALL",
        "fields": ["rationale_code"],
    },
    {
        "id": "SP008_risk_overlay",
        "weight": 1,
        "overlay_fields": ["overlay_code", "primary_action", "rationale_codes"],
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


def top_level_match(expected, predicted, fields):
    mismatches = []
    for field in fields:
        if predicted.get(field) != expected.get(field):
            mismatches.append(
                {
                    "field": field,
                    "expected": expected.get(field),
                    "predicted": predicted.get(field),
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
            if pred.get(field) != exp.get(field):
                mismatches.append(
                    {
                        "opportunity_set": row_id,
                        "field": field,
                        "expected": exp.get(field),
                        "predicted": pred.get(field),
                    }
                )
    return len(mismatches) == 0, mismatches


def overlay_match(expected, predicted, fields):
    expected_overlay = expected.get("risk_overlay", {})
    predicted_overlay = predicted.get("risk_overlay", {})
    mismatches = []
    if not isinstance(predicted_overlay, dict):
        return False, [{"field": "risk_overlay", "expected": expected_overlay, "predicted": predicted_overlay}]
    for field in fields:
        if predicted_overlay.get(field) != expected_overlay.get(field):
            mismatches.append(
                {
                    "field": f"risk_overlay.{field}",
                    "expected": expected_overlay.get(field),
                    "predicted": predicted_overlay.get(field),
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
        if "fields" in point and "rows" not in point:
            matched, mismatches = top_level_match(expected, predicted, point["fields"])
        elif "rows" in point:
            row_ids = all_row_ids if point["rows"] == "ALL" else point["rows"]
            matched, mismatches = row_match(expected_rows, predicted_rows, row_ids, point["fields"])
        else:
            matched, mismatches = overlay_match(expected, predicted, point["overlay_fields"])

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
