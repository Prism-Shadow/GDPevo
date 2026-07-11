#!/usr/bin/env python3
import json
import math
import os
import sqlite3
import sys
from pathlib import Path


INCIDENT_ID = "INC-2026-006"
PRODUCT_ID = "HELIOSYNC"
SEVERITIES = ["P1", "P2", "P3", "P4"]
EXCLUSION_KEYS = [
    "usage_non_production_rows_excluded",
    "usage_backfill_rows_excluded",
    "usage_internal_or_test_account_rows_excluded",
    "usage_inactive_subscription_rows_excluded",
    "usage_telemetry_v1_overlap_rows_excluded",
    "followup_duplicate_tickets_excluded",
    "followup_canceled_tickets_excluded",
    "followup_internal_or_test_account_tickets_excluded",
    "followup_non_customer_impact_tickets_excluded",
    "followup_non_defect_category_tickets_excluded",
    "followup_inactive_subscription_tickets_excluded",
]
TOTAL_WEIGHT = 16


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def db_path() -> Path:
    env_path = os.environ.get("TASK_SQLITE_DB_PATH")
    if env_path:
        return Path(env_path)
    return repo_root() / "env" / "generated" / "ops_analytics.sqlite"


def connect():
    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row
    return con


def load_prediction(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value) or not value.is_integer():
            return None
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped != value:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def safe_int(value):
    value = as_int(value)
    return value if value is not None else 0


def make_point(point_id, weight, passed, goal):
    return {
        "id": point_id,
        "weight": weight,
        "earned": weight if passed else 0,
        "passed": bool(passed),
        "goal": goal,
    }


def report(points):
    earned = sum(point["earned"] for point in points)
    return {
        "score": round(earned / TOTAL_WEIGHT, 6),
        "earned_weight": earned,
        "total_weight": TOTAL_WEIGHT,
        "points": points,
    }


BASE_CTE = """
WITH incident AS (
  SELECT *
  FROM incidents
  WHERE incident_id = 'INC-2026-006'
),
usage_base AS (
  SELECT
    u.*,
    a.account_name,
    a.region,
    a.segment,
    a.account_status,
    a.is_internal
  FROM usage_daily u
  JOIN incident i ON i.product_id = u.product_id
  JOIN accounts a ON a.account_id = u.account_id
  WHERE u.activity_date BETWEEN date(i.started_at) AND date(i.resolved_at)
    AND (i.impacted_region = 'GLOBAL' OR a.region = i.impacted_region)
),
usage_customer_active AS (
  SELECT *
  FROM usage_base b
  WHERE b.is_internal = 0
    AND b.account_status IN ('active', 'paused')
    AND b.environment = 'production'
    AND b.is_backfill = 0
    AND EXISTS (
      SELECT 1
      FROM subscriptions s
      WHERE s.account_id = b.account_id
        AND s.product_id = b.product_id
        AND s.start_date <= b.activity_date
        AND (s.end_date IS NULL OR s.end_date >= b.activity_date)
        AND s.subscription_status IN ('active', 'paused', 'trial')
    )
),
qualified_usage AS (
  SELECT *
  FROM usage_customer_active b
  WHERE NOT (
    b.source_system = 'telemetry_v1'
    AND EXISTS (
      SELECT 1
      FROM usage_customer_active v2
      WHERE v2.account_id = b.account_id
        AND v2.product_id = b.product_id
        AND v2.activity_date = b.activity_date
        AND v2.source_system = 'telemetry_v2'
    )
  )
),
follow_base AS (
  SELECT
    t.*,
    a.account_name,
    a.region,
    a.segment,
    a.account_status,
    a.is_internal
  FROM tickets t
  JOIN incident i ON i.product_id = t.product_id
  JOIN accounts a ON a.account_id = t.account_id
  WHERE t.created_at > i.resolved_at
    AND t.created_at <= datetime(i.resolved_at, '+7 days')
    AND (i.impacted_region = 'GLOBAL' OR a.region = i.impacted_region)
),
qualified_follow AS (
  SELECT *
  FROM follow_base t
  WHERE t.is_internal = 0
    AND t.account_status IN ('active', 'paused')
    AND t.customer_impact = 1
    AND t.category IN ('bug', 'outage', 'performance', 'data_loss')
    AND t.status <> 'canceled'
    AND t.is_duplicate = 0
    AND EXISTS (
      SELECT 1
      FROM subscriptions s
      WHERE s.account_id = t.account_id
        AND s.product_id = t.product_id
        AND s.start_date <= date(t.created_at)
        AND (s.end_date IS NULL OR s.end_date >= date(t.created_at))
        AND s.subscription_status IN ('active', 'paused', 'trial')
    )
),
usage_by_account AS (
  SELECT
    account_id,
    account_name,
    region,
    COUNT(*) AS usage_row_count,
    SUM(api_calls) AS api_calls_during_incident
  FROM qualified_usage
  GROUP BY account_id, account_name, region
),
ticket_by_account AS (
  SELECT
    account_id,
    account_name,
    COUNT(*) AS followup_ticket_count,
    SUM(CASE WHEN severity = 'P1' THEN 1 ELSE 0 END) AS p1_count,
    SUM(CASE WHEN severity = 'P2' THEN 1 ELSE 0 END) AS p2_count,
    SUM(CASE WHEN severity = 'P3' THEN 1 ELSE 0 END) AS p3_count,
    SUM(CASE WHEN severity = 'P4' THEN 1 ELSE 0 END) AS p4_count
  FROM qualified_follow
  GROUP BY account_id, account_name
),
combined AS (
  SELECT
    u.account_id,
    u.account_name,
    u.api_calls_during_incident,
    COALESCE(t.followup_ticket_count, 0) AS followup_ticket_count,
    COALESCE(t.p1_count, 0) AS p1_followup_ticket_count,
    COALESCE(t.p2_count, 0) AS p2_followup_ticket_count,
    COALESCE(t.p3_count, 0) AS p3_followup_ticket_count,
    COALESCE(t.p4_count, 0) AS p4_followup_ticket_count,
    (
      u.api_calls_during_incident
      + COALESCE(t.p1_count, 0) * 100000
      + COALESCE(t.p2_count, 0) * 50000
      + COALESCE(t.p3_count, 0) * 10000
      + COALESCE(t.p4_count, 0) * 2500
    ) AS risk_score
  FROM usage_by_account u
  LEFT JOIN ticket_by_account t ON t.account_id = u.account_id
)
"""


def expected_answer():
    con = connect()
    incident = con.execute(
        """
        SELECT
          incident_id,
          product_id,
          started_at,
          resolved_at,
          impacted_region,
          date(started_at) AS usage_start_date,
          date(resolved_at) AS usage_end_date,
          datetime(resolved_at, '+7 days') AS followup_end_at
        FROM incidents
        WHERE incident_id = ?
        """,
        (INCIDENT_ID,),
    ).fetchone()

    overall = con.execute(
        BASE_CTE
        + """
        SELECT
          COUNT(DISTINCT account_id) AS impacted_account_count,
          COALESCE(SUM(api_calls), 0) AS total_api_calls_during_incident
        FROM qualified_usage
        """
    ).fetchone()

    usage_accounts = [
        {
            "account_id": row["account_id"],
            "account_name": row["account_name"],
            "region": row["region"],
            "usage_row_count": int(row["usage_row_count"]),
            "api_calls_during_incident": int(row["api_calls_during_incident"]),
        }
        for row in con.execute(
            BASE_CTE
            + """
            SELECT *
            FROM usage_by_account
            ORDER BY account_id ASC
            """
        )
    ]

    followup_tickets = [
        {
            "ticket_id": row["ticket_id"],
            "account_id": row["account_id"],
            "account_name": row["account_name"],
            "created_at": row["created_at"],
            "severity": row["severity"],
            "category": row["category"],
        }
        for row in con.execute(
            BASE_CTE
            + """
            SELECT ticket_id, account_id, account_name, created_at, severity, category
            FROM qualified_follow
            ORDER BY created_at ASC, ticket_id ASC
            """
        )
    ]

    both = [
        {
            "account_id": row["account_id"],
            "account_name": row["account_name"],
            "api_calls_during_incident": int(row["api_calls_during_incident"]),
            "followup_ticket_count": int(row["followup_ticket_count"]),
        }
        for row in con.execute(
            BASE_CTE
            + """
            SELECT
              c.account_id,
              c.account_name,
              c.api_calls_during_incident,
              c.followup_ticket_count
            FROM combined c
            WHERE c.followup_ticket_count > 0
            ORDER BY c.account_id ASC
            """
        )
    ]

    risk_accounts = []
    for idx, row in enumerate(
        con.execute(
            BASE_CTE
            + """
            SELECT *
            FROM combined
            ORDER BY risk_score DESC, api_calls_during_incident DESC, account_id ASC
            """
        ),
        start=1,
    ):
        risk_accounts.append(
            {
                "rank": idx,
                "account_id": row["account_id"],
                "account_name": row["account_name"],
                "api_calls_during_incident": int(row["api_calls_during_incident"]),
                "followup_ticket_count": int(row["followup_ticket_count"]),
                "p1_followup_ticket_count": int(row["p1_followup_ticket_count"]),
                "p2_followup_ticket_count": int(row["p2_followup_ticket_count"]),
                "p3_followup_ticket_count": int(row["p3_followup_ticket_count"]),
                "p4_followup_ticket_count": int(row["p4_followup_ticket_count"]),
                "risk_score": int(row["risk_score"]),
            }
        )

    severity_mix = {severity: 0 for severity in SEVERITIES}
    for row in con.execute(
        BASE_CTE
        + """
        SELECT severity, COUNT(*) AS n
        FROM qualified_follow
        GROUP BY severity
        """
    ):
        severity_mix[row["severity"]] = int(row["n"])

    exclusion_rows = con.execute(
        BASE_CTE
        + """
        SELECT 'usage_non_production_rows_excluded' AS metric, COUNT(*) AS value
        FROM usage_base
        WHERE environment <> 'production'
        UNION ALL
        SELECT 'usage_backfill_rows_excluded', COUNT(*)
        FROM usage_base
        WHERE environment = 'production' AND is_backfill = 1
        UNION ALL
        SELECT 'usage_internal_or_test_account_rows_excluded', COUNT(*)
        FROM usage_base
        WHERE is_internal = 1 OR account_status = 'test' OR segment = 'internal'
        UNION ALL
        SELECT 'usage_inactive_subscription_rows_excluded', COUNT(*)
        FROM usage_base b
        WHERE b.is_internal = 0
          AND b.account_status IN ('active', 'paused')
          AND b.environment = 'production'
          AND b.is_backfill = 0
          AND NOT EXISTS (
            SELECT 1
            FROM subscriptions s
            WHERE s.account_id = b.account_id
              AND s.product_id = b.product_id
              AND s.start_date <= b.activity_date
              AND (s.end_date IS NULL OR s.end_date >= b.activity_date)
              AND s.subscription_status IN ('active', 'paused', 'trial')
          )
        UNION ALL
        SELECT 'usage_telemetry_v1_overlap_rows_excluded', COUNT(*)
        FROM usage_customer_active b
        WHERE b.source_system = 'telemetry_v1'
          AND EXISTS (
            SELECT 1
            FROM usage_customer_active v2
            WHERE v2.account_id = b.account_id
              AND v2.product_id = b.product_id
              AND v2.activity_date = b.activity_date
              AND v2.source_system = 'telemetry_v2'
          )
        UNION ALL
        SELECT 'followup_duplicate_tickets_excluded', COUNT(*)
        FROM follow_base
        WHERE is_duplicate = 1
        UNION ALL
        SELECT 'followup_canceled_tickets_excluded', COUNT(*)
        FROM follow_base
        WHERE status = 'canceled'
        UNION ALL
        SELECT 'followup_internal_or_test_account_tickets_excluded', COUNT(*)
        FROM follow_base
        WHERE is_internal = 1 OR account_status = 'test' OR segment = 'internal'
        UNION ALL
        SELECT 'followup_non_customer_impact_tickets_excluded', COUNT(*)
        FROM follow_base
        WHERE customer_impact = 0
        UNION ALL
        SELECT 'followup_non_defect_category_tickets_excluded', COUNT(*)
        FROM follow_base
        WHERE category NOT IN ('bug', 'outage', 'performance', 'data_loss')
        UNION ALL
        SELECT 'followup_inactive_subscription_tickets_excluded', COUNT(*)
        FROM follow_base t
        WHERE t.is_internal = 0
          AND t.account_status IN ('active', 'paused')
          AND NOT EXISTS (
            SELECT 1
            FROM subscriptions s
            WHERE s.account_id = t.account_id
              AND s.product_id = t.product_id
              AND s.start_date <= date(t.created_at)
              AND (s.end_date IS NULL OR s.end_date >= date(t.created_at))
              AND s.subscription_status IN ('active', 'paused', 'trial')
          )
        """
    ).fetchall()
    exclusions = {row["metric"]: int(row["value"]) for row in exclusion_rows}

    return {
        "incident_id": incident["incident_id"],
        "product_id": incident["product_id"],
        "incident_window": {
            "started_at": incident["started_at"],
            "resolved_at": incident["resolved_at"],
            "impacted_region": incident["impacted_region"],
            "usage_start_date": incident["usage_start_date"],
            "usage_end_date": incident["usage_end_date"],
        },
        "followup_window": {
            "start_at": incident["resolved_at"],
            "end_at": incident["followup_end_at"],
        },
        "impacted_account_count": int(overall["impacted_account_count"]),
        "total_api_calls_during_incident": int(overall["total_api_calls_during_incident"]),
        "followup_ticket_count": len(followup_tickets),
        "qualified_usage_accounts": usage_accounts,
        "followup_tickets": followup_tickets,
        "accounts_with_both_signals": both,
        "highest_risk_accounts": risk_accounts,
        "severity_mix": severity_mix,
        "exclusions": exclusions,
    }


def normalize_usage_accounts(value):
    if not isinstance(value, list):
        return None
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return None
        rows.append(
            {
                "account_id": item.get("account_id"),
                "account_name": item.get("account_name"),
                "region": item.get("region"),
                "usage_row_count": as_int(item.get("usage_row_count")),
                "api_calls_during_incident": as_int(item.get("api_calls_during_incident")),
            }
        )
    return rows


def normalize_followup_tickets(value):
    if not isinstance(value, list):
        return None
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return None
        rows.append(
            {
                "ticket_id": item.get("ticket_id"),
                "account_id": item.get("account_id"),
                "account_name": item.get("account_name"),
                "created_at": item.get("created_at"),
                "severity": item.get("severity"),
                "category": item.get("category"),
            }
        )
    return rows


def normalize_both(value):
    if not isinstance(value, list):
        return None
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return None
        rows.append(
            {
                "account_id": item.get("account_id"),
                "account_name": item.get("account_name"),
                "api_calls_during_incident": as_int(item.get("api_calls_during_incident")),
                "followup_ticket_count": as_int(item.get("followup_ticket_count")),
            }
        )
    return rows


def normalize_risk(value):
    if not isinstance(value, list):
        return None
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return None
        rows.append(
            {
                "rank": as_int(item.get("rank")),
                "account_id": item.get("account_id"),
                "account_name": item.get("account_name"),
                "api_calls_during_incident": as_int(item.get("api_calls_during_incident")),
                "followup_ticket_count": as_int(item.get("followup_ticket_count")),
                "p1_followup_ticket_count": as_int(item.get("p1_followup_ticket_count")),
                "p2_followup_ticket_count": as_int(item.get("p2_followup_ticket_count")),
                "p3_followup_ticket_count": as_int(item.get("p3_followup_ticket_count")),
                "p4_followup_ticket_count": as_int(item.get("p4_followup_ticket_count")),
                "risk_score": as_int(item.get("risk_score")),
            }
        )
    return rows


def normalize_severity_mix(value):
    if not isinstance(value, dict):
        return None
    normalized = {}
    for severity in SEVERITIES:
        count = as_int(value.get(severity))
        if count is None:
            return None
        normalized[severity] = count
    return normalized


def normalize_exclusions(value):
    if not isinstance(value, dict):
        return None
    normalized = {}
    for key in EXCLUSION_KEYS:
        count = as_int(value.get(key))
        if count is None:
            return None
        normalized[key] = count
    return normalized


def metadata_ok(pred, exp):
    if not isinstance(pred, dict):
        return False
    if pred.get("incident_id") != INCIDENT_ID or pred.get("product_id") != PRODUCT_ID:
        return False
    return (
        pred.get("incident_window") == exp["incident_window"]
        and pred.get("followup_window") == exp["followup_window"]
        and isinstance(pred.get("qualified_usage_accounts"), list)
        and isinstance(pred.get("followup_tickets"), list)
        and isinstance(pred.get("accounts_with_both_signals"), list)
        and isinstance(pred.get("highest_risk_accounts"), list)
        and isinstance(pred.get("severity_mix"), dict)
        and isinstance(pred.get("exclusions"), dict)
    )


def numbers_ok(pred, exp):
    return (
        as_int(pred.get("impacted_account_count")) == exp["impacted_account_count"]
        and as_int(pred.get("total_api_calls_during_incident"))
        == exp["total_api_calls_during_incident"]
        and as_int(pred.get("followup_ticket_count")) == exp["followup_ticket_count"]
    )


def main():
    if len(sys.argv) != 2:
        print(json.dumps(report([make_point("ERR", 0, False, "Usage: evaluate.py <prediction.json>")])))
        return 0

    try:
        pred = load_prediction(sys.argv[1])
        exp = expected_answer()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": TOTAL_WEIGHT,
                    "points": [],
                    "error": f"could not load prediction or expected answer: {exc}",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    usage_ok = (
        normalize_usage_accounts(pred.get("qualified_usage_accounts"))
        == exp["qualified_usage_accounts"]
        and as_int(pred.get("impacted_account_count")) == exp["impacted_account_count"]
    )
    api_ok = (
        as_int(pred.get("total_api_calls_during_incident"))
        == exp["total_api_calls_during_incident"]
    )
    followup_ok = (
        normalize_followup_tickets(pred.get("followup_tickets")) == exp["followup_tickets"]
        and as_int(pred.get("followup_ticket_count")) == exp["followup_ticket_count"]
    )
    both_ok = normalize_both(pred.get("accounts_with_both_signals")) == exp["accounts_with_both_signals"]
    risk_ok = normalize_risk(pred.get("highest_risk_accounts")) == exp["highest_risk_accounts"]
    severity_ok = normalize_severity_mix(pred.get("severity_mix")) == exp["severity_mix"]
    exclusions_ok = normalize_exclusions(pred.get("exclusions")) == exp["exclusions"]
    schema_ok = metadata_ok(pred, exp) and numbers_ok(pred, exp)

    points = [
        make_point("SP001", 3, usage_ok, "Qualified incident-window production usage accounts and per-account API calls are exact."),
        make_point("SP002", 2, api_ok, "Total incident-window API calls are exact."),
        make_point("SP003", 2, followup_ok, "Qualified follow-up customer-impacting defect ticket set and count are exact."),
        make_point("SP004", 3, both_ok, "Accounts with both incident usage and follow-up tickets are exact."),
        make_point("SP005", 2, risk_ok, "Highest-risk account ranking and risk metrics are exact."),
        make_point("SP006", 1, severity_ok, "Follow-up ticket severity mix is exact."),
        make_point("SP007", 2, exclusions_ok, "Usage and ticket exclusion counters are exact."),
        make_point("SP008", 1, schema_ok, "Prediction follows the required metadata and JSON structure."),
    ]
    print(json.dumps(report(points), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
