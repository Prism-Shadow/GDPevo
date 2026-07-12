#!/usr/bin/env python3
import json
import sys
from decimal import Decimal
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
EXPECTED_PATH = TASK_DIR / "output" / "answer.json"
CELL_KEY = ("clinic_id", "quarter", "plan_type", "service_category")
RATE_KEY = ("check_date", "plan_type", "service_category", "cpt_code", "state")


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value):
    if isinstance(value, dict):
        return {key: normalize(val) for key, val in sorted(value.items())}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value)).normalize()
    return value


def sort_rows(rows, key_fields):
    if not isinstance(rows, list):
        return rows
    return sorted(rows, key=lambda row: tuple(str(row.get(field, "")) for field in key_fields))


def pick(rows, fields):
    if not isinstance(rows, list):
        return rows
    return [{field: row.get(field) for field in fields} for row in rows]


def point(point_id, description, weight, expected, actual):
    matched = normalize(expected) == normalize(actual)
    return {
        "id": point_id,
        "description": description,
        "weight": weight,
        "earned": weight if matched else 0,
        "matched": matched,
    }


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "max_score": 1.0,
                    "raw_score": 0,
                    "raw_max_score": 13,
                    "error": "Usage: evaluator.py /path/to/prediction.json",
                    "points": [],
                }
            )
        )
        return 2

    try:
        expected = load_json(EXPECTED_PATH)
        actual = load_json(sys.argv[1])
    except Exception as exc:
        print(
            json.dumps(
                {"score": 0.0, "max_score": 1.0, "raw_score": 0, "raw_max_score": 13, "error": str(exc), "points": []}
            )
        )
        return 1

    exp_summary = expected.get("summary", {})
    act_summary = actual.get("summary", {})
    exp_cells = sort_rows(exp_summary.get("audit_cells", []), CELL_KEY)
    act_cells = sort_rows(act_summary.get("audit_cells", []), CELL_KEY)

    cell_metric_fields = [
        "clinic_id",
        "quarter",
        "payer",
        "plan_type",
        "service_category",
        "paid_encounter_count",
        "paid_units",
        "paid_amount",
        "benchmark_amount",
        "paid_per_unit",
        "benchmark_per_unit",
        "underpayment_amount",
        "variance_pct",
    ]
    material_fields = [
        "clinic_id",
        "quarter",
        "payer",
        "plan_type",
        "service_category",
        "paid_units",
        "paid_amount",
        "benchmark_amount",
        "paid_per_unit",
        "benchmark_per_unit",
        "underpayment_amount",
        "variance_pct",
    ]
    handling_fields = [
        "clinic_id",
        "quarter",
        "payer",
        "plan_type",
        "service_category",
        "excluded_encounter_count",
        "open_recovery_amount",
        "active_recovery_amount",
        "correction_count",
    ]
    total_fields = [
        "cells_analyzed",
        "material_underpaid_cell_count",
        "total_paid_units",
        "total_paid_amount",
        "total_benchmark_amount",
        "total_material_underpayment_amount",
    ]
    recovery_total_fields = ["total_open_recovery_amount", "total_recovery_opportunity_amount"]
    ranking_fields = [
        "rank",
        "clinic_id",
        "quarter",
        "plan_type",
        "service_category",
        "material_underpayment_amount",
        "open_recovery_amount",
        "total_recovery_opportunity",
    ]

    points = [
        point(
            "SP001_active_rate_sources",
            "Requested active rate schedule selections",
            3,
            sort_rows(expected.get("rate_source_checks", []), RATE_KEY),
            sort_rows(actual.get("rate_source_checks", []), RATE_KEY),
        ),
        point(
            "SP002_paid_and_benchmark_variance",
            "Paid-unit and benchmark variance metrics for audit cells",
            2,
            pick(exp_cells, cell_metric_fields),
            pick(act_cells, cell_metric_fields),
        ),
        point(
            "SP003_material_underpaid_cells",
            "Material underpayment set and values",
            2,
            sort_rows(pick(expected.get("underpaid_cells", []), material_fields), CELL_KEY),
            sort_rows(pick(actual.get("underpaid_cells", []), material_fields), CELL_KEY),
        ),
        point(
            "SP004_total_variance_summary",
            "Core audit variance totals excluding recovery accounting",
            2,
            {field: exp_summary.get("totals", {}).get(field) for field in total_fields},
            {field: act_summary.get("totals", {}).get(field) for field in total_fields},
        ),
        point(
            "SP005_top_five_recovery_opportunity_ranking",
            "Top five recovery opportunity ranking",
            2,
            pick(expected.get("summary", {}).get("recovery_opportunity_ranking", [])[:5], ranking_fields),
            pick(actual.get("summary", {}).get("recovery_opportunity_ranking", [])[:5], ranking_fields),
        ),
        point(
            "SP006_correction_handling",
            "Denied, unpaid, and correction handling",
            1,
            {
                "cell_handling": pick(exp_cells, handling_fields),
                "correction_handling": exp_summary.get("correction_handling", {}),
            },
            {
                "cell_handling": pick(act_cells, handling_fields),
                "correction_handling": act_summary.get("correction_handling", {}),
            },
        ),
        point(
            "SP007_recovery_totals",
            "Recovery totals",
            1,
            {field: exp_summary.get("totals", {}).get(field) for field in recovery_total_fields},
            {field: act_summary.get("totals", {}).get(field) for field in recovery_total_fields},
        ),
    ]

    raw_score = sum(item["earned"] for item in points)
    raw_max = sum(item["weight"] for item in points)
    print(
        json.dumps(
            {
                "score": raw_score / raw_max if raw_max else 0.0,
                "max_score": 1.0,
                "raw_score": raw_score,
                "raw_max_score": raw_max,
                "points": points,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
