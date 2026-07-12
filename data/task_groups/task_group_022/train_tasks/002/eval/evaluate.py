#!/usr/bin/env python3
import json
import math
import os
import sqlite3
import statistics
import sys
from pathlib import Path


TOTAL_WEIGHT = 16


def report(points):
    earned = sum(point["earned"] for point in points)
    return {
        "score": round(earned / TOTAL_WEIGHT, 6),
        "earned_weight": earned,
        "total_weight": TOTAL_WEIGHT,
        "points": points,
    }


def point(point_id, weight, passed, goal):
    return {
        "id": point_id,
        "weight": weight,
        "earned": weight if passed else 0,
        "passed": bool(passed),
        "goal": goal,
    }


def load_prediction(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def db_path():
    env_path = os.environ.get("TASK_SQLITE_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[3] / "env" / "generated" / "ops_analytics.sqlite"


def round_half_up(value, places):
    return round(float(value) + 0.0, places)


def expected_answer():
    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row
    base_from = """
        FROM tickets t
        JOIN accounts a ON a.account_id = t.account_id
        WHERE t.product_id = 'HELIOSYNC'
          AND t.created_at >= '2026-03-01'
          AND t.created_at < '2026-04-01'
    """
    qualified_where = """
          AND a.is_internal = 0
          AND a.account_status <> 'test'
          AND a.segment <> 'internal'
          AND t.customer_impact = 1
          AND t.category IN ('bug', 'outage', 'performance', 'data_loss')
          AND t.status <> 'canceled'
          AND t.is_duplicate = 0
    """
    rows = list(con.execute(
        """
        SELECT
          t.ticket_id,
          t.account_id,
          a.account_name,
          t.status,
          t.severity,
          t.created_at,
          t.closed_at,
          t.sla_due_at,
          CASE
            WHEN t.closed_at IS NOT NULL THEN (julianday(t.closed_at) - julianday(t.created_at)) * 24.0
            ELSE NULL
          END AS close_hours,
          CASE
            WHEN t.closed_at IS NOT NULL AND t.closed_at > t.sla_due_at THEN 1
            WHEN t.closed_at IS NULL AND t.sla_due_at < '2026-04-01 00:00:00' THEN 1
            ELSE 0
          END AS sla_breached
        """ + base_from + qualified_where + """
        ORDER BY t.ticket_id
        """
    ))

    qualified_ids = [row["ticket_id"] for row in rows]
    p1_p2_open = sum(
        1 for row in rows
        if row["severity"] in {"P1", "P2"} and row["status"] in {"open", "in_progress"}
    )
    breach_count = sum(row["sla_breached"] for row in rows)
    closed_hours = [row["close_hours"] for row in rows if row["close_hours"] is not None]

    top_accounts = []
    for row in con.execute(
        """
        SELECT
          t.account_id,
          a.account_name,
          COUNT(*) AS ticket_count,
          SUM(CASE WHEN t.severity IN ('P1', 'P2') THEN 1 ELSE 0 END) AS p1_p2_count,
          SUM(CASE
            WHEN t.closed_at IS NOT NULL AND t.closed_at > t.sla_due_at THEN 1
            WHEN t.closed_at IS NULL AND t.sla_due_at < '2026-04-01 00:00:00' THEN 1
            ELSE 0
          END) AS sla_breach_count
        """ + base_from + qualified_where + """
        GROUP BY t.account_id, a.account_name
        ORDER BY ticket_count DESC, t.account_id ASC
        LIMIT 5
        """
    ):
        top_accounts.append({
            "account_id": row["account_id"],
            "account_name": row["account_name"],
            "ticket_count": int(row["ticket_count"]),
            "p1_p2_count": int(row["p1_p2_count"]),
            "sla_breach_count": int(row["sla_breach_count"]),
        })

    exclusion_sql = {
        "duplicate": "t.is_duplicate = 1",
        "canceled": "t.status = 'canceled'",
        "internal_or_test_account": "(a.is_internal = 1 OR a.account_status = 'test' OR a.segment = 'internal')",
        "non_customer_impact": "t.customer_impact = 0",
        "non_defect_category": "t.category NOT IN ('bug', 'outage', 'performance', 'data_loss')",
    }
    excluded_counts = {}
    for key, condition in exclusion_sql.items():
        excluded_counts[key] = int(con.execute(
            "SELECT COUNT(*) " + base_from + " AND " + condition
        ).fetchone()[0])

    return {
        "product_id": "HELIOSYNC",
        "period": {"start_date": "2026-03-01", "end_date": "2026-03-31"},
        "qualified_ticket_count": len(rows),
        "qualified_ticket_ids": sorted(qualified_ids),
        "p1_p2_open_count": p1_p2_open,
        "sla_breach_rate": round_half_up(breach_count / len(rows), 4) if rows else 0.0,
        "top_accounts": top_accounts,
        "excluded_duplicate_count": excluded_counts["duplicate"],
        "excluded_counts": excluded_counts,
        "median_close_hours": round_half_up(statistics.median(closed_hours), 2) if closed_hours else None,
    }


def as_int(value):
    try:
        if isinstance(value, bool):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def as_float(value):
    try:
        if isinstance(value, bool):
            return None
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    except (TypeError, ValueError):
        return None


def normalized_top_accounts(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        normalized.append({
            "account_id": item.get("account_id"),
            "account_name": item.get("account_name"),
            "ticket_count": as_int(item.get("ticket_count")),
            "p1_p2_count": as_int(item.get("p1_p2_count")),
            "sla_breach_count": as_int(item.get("sla_breach_count")),
        })
    return normalized


def main():
    if len(sys.argv) != 2:
        print(json.dumps(report([
            point("ERR", 0, False, "Usage: evaluate.py <prediction.json>")
        ])))
        return

    try:
        prediction = load_prediction(sys.argv[1])
        expected = expected_answer()
    except Exception as exc:
        print(json.dumps(report([
            point("ERR", 0, False, f"Could not load prediction or database: {exc}")
        ])))
        return

    required_keys = {
        "product_id",
        "period",
        "qualified_ticket_count",
        "qualified_ticket_ids",
        "p1_p2_open_count",
        "sla_breach_rate",
        "top_accounts",
        "excluded_duplicate_count",
        "excluded_counts",
        "median_close_hours",
    }
    schema_ok = isinstance(prediction, dict) and required_keys.issubset(prediction.keys())
    if schema_ok:
        schema_ok = (
            prediction.get("product_id") == "HELIOSYNC"
            and isinstance(prediction.get("period"), dict)
            and prediction["period"].get("start_date") == "2026-03-01"
            and prediction["period"].get("end_date") == "2026-03-31"
            and isinstance(prediction.get("qualified_ticket_ids"), list)
            and isinstance(prediction.get("top_accounts"), list)
            and isinstance(prediction.get("excluded_counts"), dict)
        )

    pred_ids = prediction.get("qualified_ticket_ids") if isinstance(prediction, dict) else None
    ids_ok = (
        isinstance(pred_ids, list)
        and sorted(str(item) for item in pred_ids) == expected["qualified_ticket_ids"]
        and as_int(prediction.get("qualified_ticket_count")) == expected["qualified_ticket_count"]
    )

    p1_p2_ok = as_int(prediction.get("p1_p2_open_count")) == expected["p1_p2_open_count"]

    breach_value = as_float(prediction.get("sla_breach_rate"))
    breach_ok = breach_value is not None and round_half_up(breach_value, 4) == expected["sla_breach_rate"]

    top_ok = normalized_top_accounts(prediction.get("top_accounts")) == expected["top_accounts"]

    duplicate_ok = (
        as_int(prediction.get("excluded_duplicate_count")) == expected["excluded_duplicate_count"]
        and isinstance(prediction.get("excluded_counts"), dict)
        and as_int(prediction["excluded_counts"].get("duplicate")) == expected["excluded_counts"]["duplicate"]
        and not any(ticket_id.startswith("DUP-") for ticket_id in expected["qualified_ticket_ids"])
    )

    median_value = as_float(prediction.get("median_close_hours"))
    median_ok = median_value is not None and round_half_up(median_value, 2) == expected["median_close_hours"]

    exclusion_keys = [
        "canceled",
        "internal_or_test_account",
        "non_customer_impact",
        "non_defect_category",
    ]
    excluded_counts = prediction.get("excluded_counts")
    exclusions_ok = isinstance(excluded_counts, dict) and all(
        as_int(excluded_counts.get(key)) == expected["excluded_counts"][key]
        for key in exclusion_keys
    )

    points = [
        point("SP001", 3, ids_ok, "Qualified HelioSync March ticket set and count are exact."),
        point("SP002", 2, p1_p2_ok, "P1/P2 open or in-progress qualified ticket count is exact."),
        point("SP003", 3, breach_ok, "SLA breach rate is exact to 4 decimal places."),
        point("SP004", 2, top_ok, "Top affected account ranking and account metrics are exact."),
        point("SP005", 1, duplicate_ok, "Duplicate ticket exclusions are reflected correctly."),
        point("SP006", 2, median_ok, "Median close hours is exact to 2 decimal places."),
        point("SP007", 2, exclusions_ok, "Canceled, internal/test, non-customer, and non-defect exclusions are reflected correctly."),
        point("SP008", 1, schema_ok, "Prediction follows the required JSON schema and period/product fields."),
    ]
    print(json.dumps(report(points), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
