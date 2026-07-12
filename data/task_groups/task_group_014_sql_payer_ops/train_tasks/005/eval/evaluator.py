#!/usr/bin/env python3
import json
import sys
from decimal import Decimal
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
EXPECTED_PATH = TASK_DIR / "output" / "answer.json"
CELL_KEY = ("clinic_id", "plan_type", "service_category")


def load_json(path):
    with open(path, encoding="utf-8") as handle:
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


def sort_by_cell(rows):
    if not isinstance(rows, list):
        return rows
    return sorted(rows, key=lambda row: tuple(row.get(key, "") for key in CELL_KEY))


def pick(rows, fields):
    return [{field: row.get(field) for field in fields} for row in rows]


def point(point_id, description, weight, expected_value, actual_value):
    matched = normalize(expected_value) == normalize(actual_value)
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
        actual = load_json(Path(sys.argv[1]))
    except Exception as exc:
        print(
            json.dumps(
                {"score": 0.0, "max_score": 1.0, "raw_score": 0, "raw_max_score": 13, "error": str(exc), "points": []}
            )
        )
        return 1

    exp_summary = expected.get("portfolio_summary", {})
    act_summary = actual.get("portfolio_summary", {})
    exp_cells = sort_by_cell(exp_summary.get("payer_service_results", []))
    act_cells = sort_by_cell(act_summary.get("payer_service_results", []))

    margin_fields = [
        "clinic_id",
        "plan_type",
        "service_category",
        "encounter_count",
        "units",
        "paid_amount",
        "cost_per_unit",
        "total_cost",
        "net_revenue",
        "net_margin",
        "margin_pct",
        "budget_margin_pct",
    ]
    class_fields = ["clinic_id", "plan_type", "service_category", "budget_variance_class"]
    recovery_fields = ["clinic_id", "plan_type", "service_category", "open_recovery"]
    persistence_fields = ["clinic_id", "plan_type", "service_category", "persistence_class"]
    summary_fields = [
        "cells_analyzed",
        "flagged_pair_count",
        "total_net_revenue",
        "total_cost",
        "total_net_margin",
        "total_open_recovery_included",
        "total_projected_improvement",
    ]

    points = [
        point(
            "SP001",
            "Net margin metrics by clinic, plan type, and service category",
            3,
            pick(exp_cells, margin_fields),
            pick(act_cells, margin_fields),
        ),
        point(
            "SP002",
            "Ranked top three loss drivers",
            2,
            expected.get("ranked_loss_drivers"),
            actual.get("ranked_loss_drivers"),
        ),
        point(
            "SP003",
            "Corrective action list for major shortfall cells",
            2,
            sort_by_cell(expected.get("payer_actions", [])),
            sort_by_cell(actual.get("payer_actions", [])),
        ),
        point(
            "SP004", "Budget variance classifications", 2, pick(exp_cells, class_fields), pick(act_cells, class_fields)
        ),
        point(
            "SP005",
            "Open correction recovery inclusion",
            2,
            {
                "cell_open_recovery": pick(exp_cells, recovery_fields),
                "total_open_recovery_included": exp_summary.get("total_open_recovery_included"),
            },
            {
                "cell_open_recovery": pick(act_cells, recovery_fields),
                "total_open_recovery_included": act_summary.get("total_open_recovery_included"),
            },
        ),
        point(
            "SP006",
            "Persistent versus noise classifications",
            1,
            pick(exp_cells, persistence_fields),
            pick(act_cells, persistence_fields),
        ),
        point(
            "SP007",
            "Portfolio summary totals",
            1,
            {field: exp_summary.get(field) for field in summary_fields},
            {field: act_summary.get(field) for field in summary_fields},
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
