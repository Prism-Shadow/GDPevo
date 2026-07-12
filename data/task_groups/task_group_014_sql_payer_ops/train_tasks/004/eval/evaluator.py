#!/usr/bin/env python3
import copy
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
EXPECTED_PATH = BASE_DIR / "output" / "answer.json"

MONEY_FIELDS = {
    "minimum_underpayment_amount",
    "paid_amount",
    "benchmark_amount",
    "paid_per_unit",
    "benchmark_per_unit",
    "variance_amount",
    "tracked_recovery_amount",
    "expected_recovery_amount",
    "total_tracked_recovery_amount",
}
PCT_FIELDS = {
    "minimum_underpayment_pct",
    "variance_pct",
}

CLINIC_KEY = ("clinic_id", "quarter")
FLAG_KEY = ("quarter", "clinic_id", "payer", "plan_type", "service_category")


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def round_decimal(value, places):
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return value
    quantum = Decimal("1").scaleb(-places)
    rounded = decimal_value.quantize(quantum, rounding=ROUND_HALF_UP)
    return float(rounded)


def normalize_numbers(obj, key_name=None):
    if isinstance(obj, dict):
        return {key: normalize_numbers(value, key) for key, value in obj.items()}
    if isinstance(obj, list):
        return [normalize_numbers(value, key_name) for value in obj]
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if key_name in MONEY_FIELDS:
            return round_decimal(obj, 2)
        if key_name in PCT_FIELDS:
            return round_decimal(obj, 4)
        return obj
    return obj


def sort_by_keys(rows, keys):
    return sorted(rows or [], key=lambda row: tuple(row.get(key) for key in keys))


def keyed(rows, keys):
    return {tuple(row.get(key) for key in keys): row for row in rows or []}


def project(row, fields):
    return {field: row.get(field) for field in fields}


def add_point(points, name, weight, expected_value, actual_value):
    passed = expected_value == actual_value
    point = {
        "name": name,
        "weight": weight,
        "earned": weight if passed else 0,
        "passed": passed,
    }
    if not passed:
        point["expected"] = expected_value
        point["actual"] = actual_value
    points.append(point)


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "max_score": 1.0,
                    "raw_score": 0,
                    "max_raw_score": 15,
                    "error": "usage: evaluator.py /path/to/prediction.json",
                    "points": [],
                }
            )
        )
        return 1

    try:
        expected = normalize_numbers(load_json(EXPECTED_PATH))
        actual = normalize_numbers(load_json(Path(sys.argv[1])))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "max_score": 1.0,
                    "raw_score": 0,
                    "max_raw_score": 15,
                    "error": f"failed to load JSON: {exc}",
                    "points": [],
                }
            )
        )
        return 0

    points = []

    add_point(
        points,
        "period_scope_and_materiality",
        1,
        expected.get("period"),
        actual.get("period"),
    )

    clinic_fields = [
        "clinic_id",
        "quarter",
        "paid_encounters",
        "paid_units",
        "paid_amount",
        "benchmark_amount",
        "variance_amount",
        "variance_pct",
        "material_underpayment_cells",
        "compliance_classification",
    ]
    expected_clinics = [
        project(row, clinic_fields) for row in sort_by_keys(expected.get("clinic_results"), CLINIC_KEY)
    ]
    actual_clinics = [project(row, clinic_fields) for row in sort_by_keys(actual.get("clinic_results"), CLINIC_KEY)]
    add_point(points, "clinic_quarter_paid_benchmark_results", 2, expected_clinics, actual_clinics)

    recovery_fields = [
        "clinic_id",
        "quarter",
        "excluded_denied_or_unpaid_encounters",
        "tracked_recovery_amount",
    ]
    expected_recovery = [
        project(row, recovery_fields) for row in sort_by_keys(expected.get("clinic_results"), CLINIC_KEY)
    ]
    actual_recovery = [project(row, recovery_fields) for row in sort_by_keys(actual.get("clinic_results"), CLINIC_KEY)]
    add_point(points, "excluded_denied_unpaid_recovery_tracking", 2, expected_recovery, actual_recovery)

    expected_flag_map = keyed(expected.get("flagged_variances"), FLAG_KEY)
    actual_flag_map = keyed(actual.get("flagged_variances"), FLAG_KEY)
    add_point(
        points,
        "material_underpayment_cell_identity",
        2,
        sorted(expected_flag_map),
        sorted(actual_flag_map),
    )

    metric_fields = [
        "quarter",
        "clinic_id",
        "payer",
        "plan_type",
        "service_category",
        "paid_encounters",
        "paid_units",
        "paid_amount",
        "benchmark_amount",
        "paid_per_unit",
        "benchmark_per_unit",
        "variance_amount",
        "variance_pct",
        "compliance_classification",
    ]
    expected_metrics = [
        project(row, metric_fields) for row in sort_by_keys(expected.get("flagged_variances"), FLAG_KEY)
    ]
    actual_metrics = [project(row, metric_fields) for row in sort_by_keys(actual.get("flagged_variances"), FLAG_KEY)]
    add_point(points, "material_underpayment_cell_metrics", 3, expected_metrics, actual_metrics)

    rate_fields = [
        "quarter",
        "clinic_id",
        "payer",
        "plan_type",
        "service_category",
        "rate_schedule_rate_ids",
    ]

    def normalize_rate_rows(rows):
        normalized = []
        for row in rows or []:
            item = copy.deepcopy(project(row, rate_fields))
            item["rate_schedule_rate_ids"] = sorted(item.get("rate_schedule_rate_ids") or [])
            normalized.append(item)
        return sort_by_keys(normalized, FLAG_KEY)

    add_point(
        points,
        "active_rate_schedule_ids_for_flagged_cells",
        3,
        normalize_rate_rows(expected.get("flagged_variances")),
        normalize_rate_rows(actual.get("flagged_variances")),
    )

    add_point(
        points,
        "top_recovery_opportunity",
        1,
        expected.get("top_recovery_opportunity"),
        actual.get("top_recovery_opportunity"),
    )

    add_point(
        points,
        "summary_counts_and_recovery_total",
        1,
        expected.get("summary"),
        actual.get("summary"),
    )

    raw_score = sum(point["earned"] for point in points)
    max_raw_score = sum(point["weight"] for point in points)
    result = {
        "score": round(raw_score / max_raw_score, 6),
        "max_score": 1.0,
        "raw_score": raw_score,
        "max_raw_score": max_raw_score,
        "points": points,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
