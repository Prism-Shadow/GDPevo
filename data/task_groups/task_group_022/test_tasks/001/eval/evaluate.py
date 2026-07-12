#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from pathlib import Path


LOW_ADOPTION_THRESHOLD = 1100.00
START_DATE = "2026-04-01"
END_DATE = "2026-06-30"
PRODUCT_ID = "NEXAQUEUE"
SEGMENT = "commercial"
REGION = "NA"


def task_group_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "env" / "generated" / "ops_analytics.sqlite").exists():
            return parent
    return here.parents[3]


def db_path() -> Path:
    env_path = os.environ.get("TASK_SQLITE_DB_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    return task_group_root() / "env" / "generated" / "ops_analytics.sqlite"


def rows_to_dicts(cursor):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def expected_answer():
    con = sqlite3.connect(db_path())
    cte = f"""
    WITH base AS (
      SELECT
        u.*,
        a.account_name,
        a.region,
        a.account_status,
        a.is_internal,
        s.subscription_id,
        s.subscription_status,
        s.start_date AS subscription_start_date,
        s.end_date AS subscription_end_date,
        EXISTS (
          SELECT 1
          FROM usage_daily u2
          WHERE u2.account_id = u.account_id
            AND u2.product_id = u.product_id
            AND u2.activity_date = u.activity_date
            AND u2.is_backfill = 0
            AND u2.source_system = 'telemetry_v2'
        ) AS has_v2_same_day
      FROM usage_daily u
      JOIN accounts a ON a.account_id = u.account_id
      LEFT JOIN subscriptions s
        ON s.account_id = u.account_id
       AND s.product_id = u.product_id
      WHERE u.product_id = '{PRODUCT_ID}'
        AND u.activity_date BETWEEN '{START_DATE}' AND '{END_DATE}'
        AND a.region = '{REGION}'
        AND a.segment = '{SEGMENT}'
        AND a.is_internal = 0
        AND a.account_status <> 'test'
    ),
    qualified AS (
      SELECT *
      FROM base
      WHERE environment = 'production'
        AND is_backfill = 0
        AND NOT (source_system = 'telemetry_v1' AND has_v2_same_day)
        AND subscription_id IS NOT NULL
        AND subscription_status IN ('active', 'trial')
        AND subscription_start_date <= activity_date
        AND (subscription_end_date IS NULL OR subscription_end_date >= activity_date)
    )
    """
    account_sql = (
        cte
        + """
    SELECT
      account_id,
      account_name,
      subscription_start_date,
      subscription_end_date,
      COUNT(*) AS qualified_usage_rows,
      ROUND(SUM(compute_hours), 2) AS compute_hours,
      SUM(api_calls) AS api_calls
    FROM qualified
    GROUP BY account_id, account_name, subscription_start_date, subscription_end_date
    ORDER BY compute_hours DESC, account_id ASC
    """
    )
    accounts = rows_to_dicts(con.execute(account_sql))

    total = rows_to_dicts(
        con.execute(
            cte
            + """
    SELECT
      COUNT(DISTINCT account_id) AS qualified_account_count,
      COUNT(*) AS qualified_usage_rows,
      ROUND(SUM(compute_hours), 2) AS total_compute_hours,
      SUM(api_calls) AS total_api_calls
    FROM qualified
    """
        )
    )[0]

    regional = rows_to_dicts(
        con.execute(
            cte
            + """
    SELECT
      region,
      COUNT(DISTINCT account_id) AS account_count,
      COUNT(*) AS qualified_usage_rows,
      ROUND(SUM(compute_hours), 2) AS compute_hours,
      SUM(api_calls) AS api_calls
    FROM qualified
    GROUP BY region
    ORDER BY region ASC
    """
        )
    )

    low = [
        {
            "account_id": r["account_id"],
            "account_name": r["account_name"],
            "compute_hours": r["compute_hours"],
            "api_calls": r["api_calls"],
        }
        for r in sorted(accounts, key=lambda row: (row["compute_hours"], row["account_id"]))
        if float(r["compute_hours"]) < LOW_ADOPTION_THRESHOLD
    ]

    excluded = rows_to_dicts(
        con.execute(f"""
    WITH scoped AS (
      SELECT
        u.*,
        a.account_status,
        a.is_internal,
        s.subscription_id,
        s.subscription_status,
        s.start_date AS subscription_start_date,
        s.end_date AS subscription_end_date,
        EXISTS (
          SELECT 1
          FROM usage_daily u2
          WHERE u2.account_id = u.account_id
            AND u2.product_id = u.product_id
            AND u2.activity_date = u.activity_date
            AND u2.is_backfill = 0
            AND u2.source_system = 'telemetry_v2'
        ) AS has_v2_same_day
      FROM usage_daily u
      JOIN accounts a ON a.account_id = u.account_id
      LEFT JOIN subscriptions s
        ON s.account_id = u.account_id
       AND s.product_id = u.product_id
      WHERE u.product_id = '{PRODUCT_ID}'
        AND u.activity_date BETWEEN '{START_DATE}' AND '{END_DATE}'
        AND a.region = '{REGION}'
        AND a.segment = '{SEGMENT}'
    )
    SELECT
      SUM(CASE WHEN is_internal = 1 OR account_status = 'test' THEN 1 ELSE 0 END) AS internal_or_test_account,
      SUM(CASE WHEN is_internal = 0 AND account_status <> 'test' AND environment <> 'production' THEN 1 ELSE 0 END) AS non_production_environment,
      SUM(CASE WHEN is_internal = 0 AND account_status <> 'test' AND environment = 'production' AND is_backfill = 1 THEN 1 ELSE 0 END) AS backfill,
      SUM(CASE WHEN is_internal = 0 AND account_status <> 'test' AND environment = 'production' AND is_backfill = 0 AND source_system = 'telemetry_v1' AND has_v2_same_day THEN 1 ELSE 0 END) AS telemetry_v1_shadowed,
      SUM(CASE WHEN is_internal = 0 AND account_status <> 'test' AND environment = 'production' AND is_backfill = 0 AND NOT (source_system = 'telemetry_v1' AND has_v2_same_day) AND (subscription_id IS NULL OR subscription_status NOT IN ('active', 'trial') OR subscription_start_date > activity_date OR (subscription_end_date IS NOT NULL AND subscription_end_date < activity_date)) THEN 1 ELSE 0 END) AS outside_active_subscription
    FROM scoped
    """)
    )[0]

    return {
        "schema_version": "nexaqueue_na_commercial_q2_2026_v1",
        "product_id": PRODUCT_ID,
        "period": {"start_date": START_DATE, "end_date": END_DATE},
        "segment": SEGMENT,
        "region_scope": REGION,
        **total,
        "top_accounts": accounts,
        "low_adoption_accounts": low,
        "regional_breakdown": regional,
        "excluded_row_counts": excluded,
    }


def as_number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def number_eq(actual, expected, places=2):
    n = as_number(actual)
    if n is None:
        return False
    return round(n, places) == round(float(expected), places)


def int_eq(actual, expected):
    if isinstance(actual, bool):
        return False
    try:
        return int(actual) == int(expected)
    except (TypeError, ValueError):
        return False


def get(obj, path, default=None):
    cur = obj
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def account_ids(items):
    if not isinstance(items, list):
        return []
    return [item.get("account_id") for item in items if isinstance(item, dict)]


def compare_account_list(actual, expected, check_subscription=False):
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected):
        if not isinstance(a, dict):
            return False
        checks = [
            a.get("account_id") == e["account_id"],
            a.get("account_name") == e["account_name"],
            int_eq(a.get("qualified_usage_rows"), e.get("qualified_usage_rows", 0)),
            int_eq(a.get("api_calls"), e["api_calls"]),
            number_eq(a.get("compute_hours"), e["compute_hours"]),
        ]
        if check_subscription:
            checks.extend(
                [
                    a.get("subscription_start_date") == e["subscription_start_date"],
                    a.get("subscription_end_date") == e["subscription_end_date"],
                ]
            )
        if not all(checks):
            return False
    return True


def compare_low_list(actual, expected):
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected):
        if not isinstance(a, dict):
            return False
        if not (
            a.get("account_id") == e["account_id"]
            and a.get("account_name") == e["account_name"]
            and int_eq(a.get("api_calls"), e["api_calls"])
            and number_eq(a.get("compute_hours"), e["compute_hours"])
        ):
            return False
    return True


def compare_regional(actual, expected):
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected):
        if not isinstance(a, dict):
            return False
        if not (
            a.get("region") == e["region"]
            and int_eq(a.get("account_count"), e["account_count"])
            and int_eq(a.get("qualified_usage_rows"), e["qualified_usage_rows"])
            and int_eq(a.get("api_calls"), e["api_calls"])
            and number_eq(a.get("compute_hours"), e["compute_hours"])
        ):
            return False
    return True


def compare_exclusions(actual, expected, keys):
    if not isinstance(actual, dict):
        return False
    return all(int_eq(actual.get(k), expected[k]) for k in keys)


def add_point(points, point_id, weight, passed, goal):
    points.append(
        {
            "id": point_id,
            "weight": weight,
            "earned": weight if passed else 0,
            "passed": bool(passed),
            "goal": goal,
        }
    )


def evaluate(prediction):
    expected = expected_answer()
    points = []

    top_actual = prediction.get("top_accounts")
    expected_ids = [r["account_id"] for r in expected["top_accounts"]]
    add_point(
        points,
        "SP001",
        2,
        int_eq(prediction.get("qualified_account_count"), expected["qualified_account_count"])
        and set(account_ids(top_actual)) == set(expected_ids),
        "Return the exact qualified account count and account set.",
    )

    add_point(
        points,
        "SP002",
        3,
        number_eq(prediction.get("total_compute_hours"), expected["total_compute_hours"])
        and int_eq(prediction.get("qualified_usage_rows"), expected["qualified_usage_rows"])
        and int_eq(prediction.get("total_api_calls"), expected["total_api_calls"]),
        "Return the exact aggregate qualified usage totals.",
    )

    add_point(
        points,
        "SP003",
        3,
        compare_account_list(top_actual, expected["top_accounts"], check_subscription=False),
        "Rank all qualified accounts by compute hours with exact per-account usage metrics.",
    )

    add_point(
        points,
        "SP004",
        2,
        compare_low_list(prediction.get("low_adoption_accounts"), expected["low_adoption_accounts"]),
        "Return the exact low-adoption expansion watchlist.",
    )

    add_point(
        points,
        "SP005",
        2,
        compare_regional(prediction.get("regional_breakdown"), expected["regional_breakdown"]),
        "Return the exact regional breakdown.",
    )

    add_point(
        points,
        "SP006",
        2,
        compare_exclusions(
            prediction.get("excluded_row_counts"),
            expected["excluded_row_counts"],
            ["non_production_environment", "backfill", "telemetry_v1_shadowed"],
        ),
        "Return telemetry, backfill, and non-production exclusion counts.",
    )

    actual_by_id = {}
    if isinstance(top_actual, list):
        actual_by_id = {row.get("account_id"): row for row in top_actual if isinstance(row, dict)}
    subscription_ok = True
    for e in expected["top_accounts"]:
        a = actual_by_id.get(e["account_id"], {})
        if (
            a.get("subscription_start_date") != e["subscription_start_date"]
            or a.get("subscription_end_date") != e["subscription_end_date"]
        ):
            subscription_ok = False
    subscription_ok = subscription_ok and compare_exclusions(
        prediction.get("excluded_row_counts"),
        expected["excluded_row_counts"],
        ["outside_active_subscription"],
    )
    add_point(
        points,
        "SP007",
        2,
        subscription_ok,
        "Handle active subscription dates and report the subscription-date exclusion count.",
    )

    required_keys = {
        "schema_version",
        "product_id",
        "period",
        "segment",
        "region_scope",
        "qualified_account_count",
        "qualified_usage_rows",
        "total_compute_hours",
        "total_api_calls",
        "top_accounts",
        "low_adoption_accounts",
        "regional_breakdown",
        "excluded_row_counts",
    }
    schema_ok = (
        isinstance(prediction, dict)
        and required_keys.issubset(prediction.keys())
        and prediction.get("schema_version") == expected["schema_version"]
        and prediction.get("product_id") == PRODUCT_ID
        and prediction.get("segment") == SEGMENT
        and prediction.get("region_scope") == REGION
        and get(prediction, ["period", "start_date"]) == START_DATE
        and get(prediction, ["period", "end_date"]) == END_DATE
        and isinstance(prediction.get("top_accounts"), list)
        and isinstance(prediction.get("low_adoption_accounts"), list)
        and isinstance(prediction.get("regional_breakdown"), list)
        and isinstance(prediction.get("excluded_row_counts"), dict)
    )
    add_point(points, "SP008", 1, schema_ok, "Use the required schema, scope fields, and JSON container types.")

    earned = sum(p["earned"] for p in points)
    total = sum(p["weight"] for p in points)
    return {
        "score": earned / total if total else 0.0,
        "earned_weight": earned,
        "total_weight": total,
        "points": points,
    }


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": 17,
                    "points": [],
                    "error": "Usage: evaluate.py <prediction.json>",
                }
            )
        )
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            prediction = json.load(f)
        report = evaluate(prediction)
    except Exception as exc:
        report = {
            "score": 0.0,
            "earned_weight": 0,
            "total_weight": 17,
            "points": [],
            "error": str(exc),
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
