#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from pathlib import Path


PERIOD_START = "2026-01-01"
PERIOD_END = "2026-03-31"


def task_group_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "env" / "generated" / "ops_analytics.sqlite").exists():
            return parent
    return here.parents[3]


def db_path() -> Path:
    env_path = os.environ.get("TASK_SQLITE_DB_PATH")
    if env_path:
        return Path(env_path)
    return task_group_root() / "env" / "generated" / "ops_analytics.sqlite"


def round2(value):
    return round(float(value or 0.0) + 1e-9, 2)


def load_prediction(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def standard_answer():
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    cte = f"""
    WITH base_rows AS (
      SELECT u.*, a.account_name, a.segment, a.region, a.account_status, a.is_internal
      FROM usage_daily u
      JOIN accounts a ON a.account_id = u.account_id
      WHERE u.product_id = 'ATLASDB'
        AND u.activity_date BETWEEN '{PERIOD_START}' AND '{PERIOD_END}'
        AND a.segment = 'enterprise'
        AND a.region = 'EMEA'
        AND a.is_internal = 0
        AND a.account_status IN ('active', 'paused')
        AND u.environment = 'production'
        AND u.is_backfill = 0
        AND EXISTS (
          SELECT 1
          FROM subscriptions s
          WHERE s.account_id = u.account_id
            AND s.product_id = u.product_id
            AND s.start_date <= u.activity_date
            AND (s.end_date IS NULL OR s.end_date >= u.activity_date)
            AND s.subscription_status IN ('active', 'paused', 'trial')
        )
    ),
    qualified AS (
      SELECT *
      FROM base_rows b
      WHERE NOT (
        b.source_system = 'telemetry_v1'
        AND EXISTS (
          SELECT 1
          FROM base_rows v2
          WHERE v2.account_id = b.account_id
            AND v2.product_id = b.product_id
            AND v2.activity_date = b.activity_date
            AND v2.source_system = 'telemetry_v2'
        )
      )
    )
    """
    overall = con.execute(
        cte
        + """
        SELECT COUNT(DISTINCT account_id) AS qualified_account_count,
               ROUND(SUM(compute_hours), 2) AS total_compute_hours
        FROM qualified
        """
    ).fetchone()
    account_rows = [
        dict(row)
        for row in con.execute(
            cte
            + """
            SELECT account_id,
                   account_name,
                   region,
                   COUNT(*) AS qualified_usage_rows,
                   MIN(activity_date) AS first_qualified_usage_date,
                   MAX(activity_date) AS last_qualified_usage_date,
                   ROUND(SUM(compute_hours), 2) AS compute_hours
            FROM qualified
            GROUP BY account_id, account_name, region
            ORDER BY account_id ASC
            """
        )
    ]
    top_accounts = []
    for idx, row in enumerate(
        sorted(account_rows, key=lambda item: (-round2(item["compute_hours"]), item["account_id"])),
        start=1,
    ):
        top_accounts.append(
            {
                "rank": idx,
                "account_id": row["account_id"],
                "account_name": row["account_name"],
                "compute_hours": round2(row["compute_hours"]),
            }
        )
    regional_rows = [
        {
            "region": row["region"],
            "qualified_account_count": int(row["qualified_account_count"]),
            "qualified_usage_rows": int(row["qualified_usage_rows"]),
            "compute_hours": round2(row["compute_hours"]),
        }
        for row in con.execute(
            cte
            + """
            SELECT region,
                   COUNT(DISTINCT account_id) AS qualified_account_count,
                   COUNT(*) AS qualified_usage_rows,
                   ROUND(SUM(compute_hours), 2) AS compute_hours
            FROM qualified
            GROUP BY region
            ORDER BY region ASC
            """
        )
    ]
    v1_excluded = con.execute(
        cte
        + """
        SELECT COUNT(*) AS telemetry_v1_rows_excluded
        FROM base_rows b
        WHERE b.source_system = 'telemetry_v1'
          AND EXISTS (
            SELECT 1
            FROM base_rows v2
            WHERE v2.account_id = b.account_id
              AND v2.product_id = b.product_id
              AND v2.activity_date = b.activity_date
              AND v2.source_system = 'telemetry_v2'
          )
        """
    ).fetchone()["telemetry_v1_rows_excluded"]
    return {
        "period": {"start_date": PERIOD_START, "end_date": PERIOD_END},
        "qualified_account_count": int(overall["qualified_account_count"]),
        "total_compute_hours": round2(overall["total_compute_hours"]),
        "top_accounts": top_accounts,
        "regional_breakdown": regional_rows,
        "account_breakdown": [
            {
                "account_id": row["account_id"],
                "account_name": row["account_name"],
                "region": row["region"],
                "qualified_usage_rows": int(row["qualified_usage_rows"]),
                "first_qualified_usage_date": row["first_qualified_usage_date"],
                "last_qualified_usage_date": row["last_qualified_usage_date"],
                "compute_hours": round2(row["compute_hours"]),
            }
            for row in account_rows
        ],
        "telemetry_v1_rows_excluded": int(v1_excluded),
    }


def numeric_equal(actual, expected, decimals=2):
    try:
        return round(float(actual), decimals) == round(float(expected), decimals)
    except (TypeError, ValueError):
        return False


def account_map(answer):
    rows = answer.get("account_breakdown")
    if not isinstance(rows, list):
        return {}
    return {row.get("account_id"): row for row in rows if isinstance(row, dict)}


def same_account_breakdown(pred, expected):
    pred_rows = pred.get("account_breakdown")
    exp_rows = expected["account_breakdown"]
    if not isinstance(pred_rows, list) or len(pred_rows) != len(exp_rows):
        return False
    if [row.get("account_id") for row in pred_rows if isinstance(row, dict)] != [
        row["account_id"] for row in exp_rows
    ]:
        return False
    pred_map = account_map(pred)
    exp_map = account_map(expected)
    if set(pred_map) != set(exp_map):
        return False
    for account_id, exp in exp_map.items():
        row = pred_map[account_id]
        checks = [
            row.get("account_name") == exp["account_name"],
            row.get("region") == exp["region"],
            row.get("qualified_usage_rows") == exp["qualified_usage_rows"],
            row.get("first_qualified_usage_date") == exp["first_qualified_usage_date"],
            row.get("last_qualified_usage_date") == exp["last_qualified_usage_date"],
            numeric_equal(row.get("compute_hours"), exp["compute_hours"]),
        ]
        if not all(checks):
            return False
    return True


def same_regional_breakdown(pred, expected):
    pred_rows = pred.get("regional_breakdown")
    exp_rows = expected["regional_breakdown"]
    if not isinstance(pred_rows, list) or len(pred_rows) != len(exp_rows):
        return False
    for pred_row, exp_row in zip(pred_rows, exp_rows):
        checks = [
            isinstance(pred_row, dict),
            pred_row.get("region") == exp_row["region"],
            pred_row.get("qualified_account_count") == exp_row["qualified_account_count"],
            pred_row.get("qualified_usage_rows") == exp_row["qualified_usage_rows"],
            numeric_equal(pred_row.get("compute_hours"), exp_row["compute_hours"]),
        ]
        if not all(checks):
            return False
    return True


def same_top_accounts(pred, expected):
    pred_rows = pred.get("top_accounts")
    exp_rows = expected["top_accounts"]
    if not isinstance(pred_rows, list) or len(pred_rows) != len(exp_rows):
        return False
    for pred_row, exp_row in zip(pred_rows, exp_rows):
        checks = [
            isinstance(pred_row, dict),
            pred_row.get("rank") == exp_row["rank"],
            pred_row.get("account_id") == exp_row["account_id"],
            pred_row.get("account_name") == exp_row["account_name"],
            numeric_equal(pred_row.get("compute_hours"), exp_row["compute_hours"]),
        ]
        if not all(checks):
            return False
    return True


def schema_ok(pred):
    if not isinstance(pred, dict):
        return False
    required = [
        "period",
        "qualified_account_count",
        "total_compute_hours",
        "top_accounts",
        "regional_breakdown",
        "account_breakdown",
        "telemetry_v1_rows_excluded",
    ]
    if any(key not in pred for key in required):
        return False
    period = pred.get("period")
    if not isinstance(period, dict):
        return False
    if not isinstance(pred.get("qualified_account_count"), int):
        return False
    if not isinstance(pred.get("top_accounts"), list):
        return False
    if not isinstance(pred.get("regional_breakdown"), list):
        return False
    if not isinstance(pred.get("account_breakdown"), list):
        return False
    if not isinstance(pred.get("telemetry_v1_rows_excluded"), int):
        return False
    return period.get("start_date") == PERIOD_START and period.get("end_date") == PERIOD_END


def evaluate(pred):
    expected = standard_answer()
    points = []

    def add(point_id, weight, passed, goal):
        points.append(
            {
                "id": point_id,
                "weight": weight,
                "earned": weight if passed else 0,
                "passed": bool(passed),
                "goal": goal,
            }
        )

    pred_accounts = set(account_map(pred))
    exp_accounts = {row["account_id"] for row in expected["account_breakdown"]}
    pred_acct_0028 = account_map(pred).get("ACCT-0028", {})

    add("QUR001", 1, schema_ok(pred), "Return the required JSON schema with the exact period.")
    add(
        "QUR002",
        2,
        pred.get("qualified_account_count") == expected["qualified_account_count"]
        and pred_accounts == exp_accounts,
        "Identify the qualified AtlasDB EMEA enterprise account set.",
    )
    add(
        "QUR003",
        3,
        numeric_equal(pred.get("total_compute_hours"), expected["total_compute_hours"]),
        "Compute the total qualified compute_hours rounded to two decimals.",
    )
    add(
        "QUR004",
        3,
        same_top_accounts(pred, expected),
        "Rank top accounts by compute_hours descending, then account_id ascending.",
    )
    add(
        "QUR005",
        2,
        same_regional_breakdown(pred, expected) and same_account_breakdown(pred, expected),
        "Provide exact regional and per-account breakdown metrics.",
    )
    add(
        "QUR006",
        2,
        "ACCT-0025" not in pred_accounts
        and pred_acct_0028.get("qualified_usage_rows") == 3
        and pred_acct_0028.get("first_qualified_usage_date") == "2026-03-29"
        and numeric_equal(pred_acct_0028.get("compute_hours"), 343.85),
        "Apply active subscription effective-date handling.",
    )
    add(
        "QUR007",
        1,
        pred.get("telemetry_v1_rows_excluded") == expected["telemetry_v1_rows_excluded"],
        "Count telemetry_v1 rows excluded when telemetry_v2 exists for the same account/product/day.",
    )
    add(
        "QUR008",
        2,
        same_account_breakdown(pred, expected)
        and same_regional_breakdown(pred, expected)
        and numeric_equal(pred.get("total_compute_hours"), expected["total_compute_hours"]),
        "Exclude internal/test accounts, non-production environments, and backfill rows.",
    )

    total = sum(point["weight"] for point in points)
    earned = sum(point["earned"] for point in points)
    return {
        "score": earned / total if total else 0.0,
        "earned_weight": earned,
        "total_weight": total,
        "points": points,
    }


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "error": "usage: evaluate.py <prediction.json>"}))
        return 2
    try:
        pred = load_prediction(sys.argv[1])
        report = evaluate(pred)
    except Exception as exc:
        report = {
            "score": 0.0,
            "earned_weight": 0,
            "total_weight": 16,
            "points": [],
            "error": str(exc),
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
