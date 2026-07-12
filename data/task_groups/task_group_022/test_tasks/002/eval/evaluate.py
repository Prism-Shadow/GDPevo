#!/usr/bin/env python3
import json
import math
import os
import sqlite3
import sys
from pathlib import Path


TOTAL_WEIGHT = 16
PERIOD_START = "2026-04-01"
PERIOD_END_INCLUSIVE = "2026-06-30"
PERIOD_END_EXCLUSIVE = "2026-07-01"
PERIOD_END_TS = "2026-07-01 00:00:00"
PRODUCT_ID = "ATLASDB"
DEFECT_CATEGORIES = ("bug", "outage", "performance", "data_loss")


def make_report(points):
    earned = sum(item["earned"] for item in points)
    return {
        "score": round(earned / TOTAL_WEIGHT, 6),
        "earned_weight": earned,
        "total_weight": TOTAL_WEIGHT,
        "points": points,
    }


def make_point(point_id, weight, passed, goal):
    return {
        "id": point_id,
        "weight": weight,
        "earned": weight if passed else 0,
        "passed": bool(passed),
        "goal": goal,
    }


def db_path():
    env_path = os.environ.get("TASK_SQLITE_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[3] / "env" / "generated" / "ops_analytics.sqlite"


def load_prediction(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def round_value(value, places):
    return round(float(value) + 0.0, places)


def base_from():
    return """
        FROM tickets t
        JOIN accounts a ON a.account_id = t.account_id
        WHERE t.product_id = 'ATLASDB'
          AND t.created_at >= '2026-04-01'
          AND t.created_at < '2026-07-01'
    """


def qualified_where():
    return """
          AND a.is_internal = 0
          AND a.account_status <> 'test'
          AND a.segment <> 'internal'
          AND t.customer_impact = 1
          AND t.category IN ('bug', 'outage', 'performance', 'data_loss')
          AND t.status <> 'canceled'
          AND t.is_duplicate = 0
    """


def expected_answer():
    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row

    rows = list(con.execute(
        """
        SELECT
          t.ticket_id,
          t.account_id,
          a.account_name,
          t.status,
          t.severity,
          t.linked_incident_id,
          CASE
            WHEN t.closed_at IS NOT NULL AND t.closed_at > t.sla_due_at THEN 1
            WHEN t.closed_at IS NULL AND t.sla_due_at < '2026-07-01 00:00:00' THEN 1
            ELSE 0
          END AS sla_breached
        """ + base_from() + qualified_where() + """
        ORDER BY t.ticket_id
        """
    ))

    qualified_ids = [row["ticket_id"] for row in rows]
    incident_linked_ids = [
        row["ticket_id"]
        for row in rows
        if row["linked_incident_id"] is not None
    ]
    breach_count = sum(row["sla_breached"] for row in rows)
    p1_p2_open = sum(
        1 for row in rows
        if row["severity"] in {"P1", "P2"} and row["status"] in {"open", "in_progress"}
    )

    top_accounts = []
    for row in con.execute(
        """
        SELECT
          t.account_id,
          a.account_name,
          COUNT(*) AS ticket_count,
          SUM(CASE WHEN t.severity IN ('P1', 'P2') THEN 1 ELSE 0 END) AS p1_p2_count,
          SUM(CASE WHEN t.linked_incident_id IS NOT NULL THEN 1 ELSE 0 END) AS incident_linked_count,
          SUM(CASE
            WHEN t.closed_at IS NOT NULL AND t.closed_at > t.sla_due_at THEN 1
            WHEN t.closed_at IS NULL AND t.sla_due_at < '2026-07-01 00:00:00' THEN 1
            ELSE 0
          END) AS sla_breach_count
        """ + base_from() + qualified_where() + """
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
            "incident_linked_count": int(row["incident_linked_count"]),
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
            "SELECT COUNT(*) " + base_from() + " AND " + condition
        ).fetchone()[0])

    return {
        "product_id": PRODUCT_ID,
        "period": {
            "start_date": PERIOD_START,
            "end_date": PERIOD_END_INCLUSIVE,
        },
        "qualified_ticket_count": len(rows),
        "qualified_ticket_ids": sorted(qualified_ids),
        "incident_linked_count": len(incident_linked_ids),
        "incident_linked_ticket_ids": sorted(incident_linked_ids),
        "sla_breach_rate": round_value(breach_count / len(rows), 4) if rows else 0.0,
        "p1_p2_open_count": p1_p2_open,
        "top_accounts": top_accounts,
        "excluded_counts": excluded_counts,
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


def normalize_string_list(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item) for item in value)


def normalize_top_accounts(value):
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
            "incident_linked_count": as_int(item.get("incident_linked_count")),
            "sla_breach_count": as_int(item.get("sla_breach_count")),
        })
    return normalized


def main():
    if len(sys.argv) != 2:
        print(json.dumps(make_report([
            make_point("ERR", 0, False, "Usage: evaluate.py <prediction.json>")
        ])))
        return

    try:
        prediction = load_prediction(sys.argv[1])
        expected = expected_answer()
    except Exception as exc:
        print(json.dumps(make_report([
            make_point("ERR", 0, False, f"Could not load prediction or database: {exc}")
        ])))
        return

    required_keys = {
        "product_id",
        "period",
        "qualified_ticket_count",
        "qualified_ticket_ids",
        "incident_linked_count",
        "incident_linked_ticket_ids",
        "sla_breach_rate",
        "p1_p2_open_count",
        "top_accounts",
        "excluded_counts",
    }
    schema_ok = isinstance(prediction, dict) and required_keys.issubset(prediction.keys())
    if schema_ok:
        excluded_counts = prediction.get("excluded_counts")
        schema_ok = (
            prediction.get("product_id") == PRODUCT_ID
            and isinstance(prediction.get("period"), dict)
            and prediction["period"].get("start_date") == PERIOD_START
            and prediction["period"].get("end_date") == PERIOD_END_INCLUSIVE
            and isinstance(prediction.get("qualified_ticket_ids"), list)
            and isinstance(prediction.get("incident_linked_ticket_ids"), list)
            and isinstance(prediction.get("top_accounts"), list)
            and isinstance(excluded_counts, dict)
            and all(key in excluded_counts for key in expected["excluded_counts"])
        )

    ids_ok = (
        normalize_string_list(prediction.get("qualified_ticket_ids")) == expected["qualified_ticket_ids"]
        and as_int(prediction.get("qualified_ticket_count")) == expected["qualified_ticket_count"]
    )

    incident_ok = (
        normalize_string_list(prediction.get("incident_linked_ticket_ids")) == expected["incident_linked_ticket_ids"]
        and as_int(prediction.get("incident_linked_count")) == expected["incident_linked_count"]
    )

    breach_value = as_float(prediction.get("sla_breach_rate"))
    breach_ok = breach_value is not None and round_value(breach_value, 4) == expected["sla_breach_rate"]

    p1_p2_ok = as_int(prediction.get("p1_p2_open_count")) == expected["p1_p2_open_count"]

    top_ok = normalize_top_accounts(prediction.get("top_accounts")) == expected["top_accounts"]

    excluded_counts = prediction.get("excluded_counts") if isinstance(prediction, dict) else None
    duplicate_canceled_ok = isinstance(excluded_counts, dict) and (
        as_int(excluded_counts.get("duplicate")) == expected["excluded_counts"]["duplicate"]
        and as_int(excluded_counts.get("canceled")) == expected["excluded_counts"]["canceled"]
    )

    account_category_ok = isinstance(excluded_counts, dict) and (
        as_int(excluded_counts.get("internal_or_test_account")) == expected["excluded_counts"]["internal_or_test_account"]
        and as_int(excluded_counts.get("non_customer_impact")) == expected["excluded_counts"]["non_customer_impact"]
        and as_int(excluded_counts.get("non_defect_category")) == expected["excluded_counts"]["non_defect_category"]
    )

    points = [
        make_point("SP001", 3, ids_ok, "Qualified AtlasDB Q2 ticket set and count are exact."),
        make_point("SP002", 2, incident_ok, "Incident-linked qualified ticket set and count are exact."),
        make_point("SP003", 3, breach_ok, "SLA breach rate is exact to 4 decimal places."),
        make_point("SP004", 2, p1_p2_ok, "P1/P2 open or in-progress qualified ticket count is exact."),
        make_point("SP005", 2, top_ok, "Top affected account ranking and account metrics are exact."),
        make_point("SP006", 2, duplicate_canceled_ok, "Duplicate and canceled exclusion counts are exact."),
        make_point("SP007", 1, account_category_ok, "Internal/test, non-customer-impact, and non-defect-category exclusion counts are exact."),
        make_point("SP008", 1, schema_ok, "Prediction follows the required JSON schema and period/product fields."),
    ]
    print(json.dumps(make_report(points), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
