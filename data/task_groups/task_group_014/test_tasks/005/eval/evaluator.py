#!/usr/bin/env python3
import json
import sys
from decimal import Decimal
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
EXPECTED_PATH = TASK_DIR / "output" / "answer.json"
CELL_KEY = ("clinic_id", "plan_type", "service_category")


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


def sort_by_cell(rows):
    if not isinstance(rows, list):
        return rows
    return sorted(rows, key=lambda row: tuple(row.get(key, "") for key in CELL_KEY))


def pick(rows, fields):
    if not isinstance(rows, list):
        return rows
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
        actual = load_json(sys.argv[1])
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "max_score": 1.0,
                    "raw_score": 0,
                    "raw_max_score": 13,
                    "error": str(exc),
                    "points": [],
                }
            )
        )
        return 1

    if not isinstance(actual, dict):
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "max_score": 1.0,
                    "raw_score": 0,
                    "raw_max_score": 13,
                    "error": "Candidate root must be a JSON object.",
                    "points": [],
                }
            )
        )
        return 1

    exp_totals = expected.get("portfolio_totals", {})
    act_totals = actual.get("portfolio_totals", {})
    exp_cells = sort_by_cell(exp_totals.get("payer_service_results", []))
    act_cells = sort_by_cell(act_totals.get("payer_service_results", []))
    exp_actions = sort_by_cell(expected.get("action_plan", []))
    act_actions = sort_by_cell(actual.get("action_plan", []))

    margin_fields = [
        "clinic_id",
        "plan_type",
        "service_category",
        "encounter_count",
        "units",
        "paid_amount",
        "open_recovery",
        "cost_per_unit",
        "total_cost",
        "net_revenue",
        "net_margin",
        "margin_pct",
        "budget_margin_pct",
    ]
    leakage_fields = [
        "clinic_id",
        "plan_type",
        "service_category",
        "authorization_denial_count",
        "authorization_leakage_encounter_count",
        "authorization_leakage_amount",
    ]
    action_fields = [
        "clinic_id",
        "plan_type",
        "service_category",
        "budget_variance_class",
        "recommended_action",
    ]
    improvement_fields = [
        "clinic_id",
        "plan_type",
        "service_category",
        "projected_improvement_after_recovery",
    ]
    persistence_fields = [
        "clinic_id",
        "plan_type",
        "service_category",
        "budget_variance_class",
        "persistence_class",
    ]
    points = [
        point(
            "SP001_margin_metrics",
            "Margin metrics by clinic, plan type, and service category",
            3,
            pick(exp_cells, margin_fields),
            pick(act_cells, margin_fields),
        ),
        point(
            "SP002_top_loss_driver_ranking",
            "Ranked top three loss drivers",
            2,
            expected.get("ranked_findings"),
            actual.get("ranked_findings"),
        ),
        point(
            "SP003_authorization_leakage",
            "Authorization leakage amounts and counts",
            2,
            {
                "cells": pick(exp_cells, leakage_fields),
                "total_authorization_leakage_amount": exp_totals.get("total_authorization_leakage_amount"),
                "authorization_leakage_encounter_count": exp_totals.get("authorization_leakage_encounter_count"),
            },
            {
                "cells": pick(act_cells, leakage_fields),
                "total_authorization_leakage_amount": act_totals.get("total_authorization_leakage_amount"),
                "authorization_leakage_encounter_count": act_totals.get("authorization_leakage_encounter_count"),
            },
        ),
        point(
            "SP004_corrective_actions",
            "Corrective action enum for flagged cells",
            2,
            pick(exp_actions, action_fields),
            pick(act_actions, action_fields),
        ),
        point(
            "SP005_projected_improvement",
            "Projected improvement after recoveries and selected actions",
            2,
            {
                "actions": pick(exp_actions, improvement_fields),
                "total_projected_improvement_after_recovery": exp_totals.get(
                    "total_projected_improvement_after_recovery"
                ),
                "total_open_recovery_included": exp_totals.get("total_open_recovery_included"),
            },
            {
                "actions": pick(act_actions, improvement_fields),
                "total_projected_improvement_after_recovery": act_totals.get(
                    "total_projected_improvement_after_recovery"
                ),
                "total_open_recovery_included": act_totals.get("total_open_recovery_included"),
            },
        ),
        point(
            "SP006_persistence_classification",
            "Persistent versus acceptable classification by cell",
            1,
            pick(exp_cells, persistence_fields),
            pick(act_cells, persistence_fields),
        ),
        point(
            "SP007_acceptable_exclusions",
            "Cells excluded from action due to acceptable margin",
            1,
            {
                "acceptable_no_action_count": exp_totals.get("acceptable_no_action_count"),
                "acceptable_no_action_cells": sort_by_cell(exp_totals.get("acceptable_no_action_cells", [])),
            },
            {
                "acceptable_no_action_count": act_totals.get("acceptable_no_action_count"),
                "acceptable_no_action_cells": sort_by_cell(act_totals.get("acceptable_no_action_cells", [])),
            },
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
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
