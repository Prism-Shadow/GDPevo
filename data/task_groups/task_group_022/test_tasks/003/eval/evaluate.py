#!/usr/bin/env python3
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path


CASE_ID = "DQ-USG-2026-05-C"
SOURCE_PRODUCT = "NEXAQUEUE"
TARGET_PRODUCT = "LUMAFORMS"
EXPECTED_AUDIT_REASON = "approved correction DQ-USG-2026-05-C"
EXPECTED_CHANGED_ROW_COUNT = 11
EXPECTED_TOTAL_COMPUTE_HOURS = 3780.05
EXPECTED_AFFECTED_ACCOUNTS = [
    {
        "account_id": "ACCT-0032",
        "account_name": "Clearline Systems EMEA 032",
        "region": "EMEA",
        "corrected_usage_row_count": 1,
        "added_compute_hours": 34.04,
    },
    {
        "account_id": "ACCT-0033",
        "account_name": "Northstar Works EMEA 033",
        "region": "EMEA",
        "corrected_usage_row_count": 1,
        "added_compute_hours": 45.98,
    },
]
EXPECTED_TOP_ACCOUNTS = [
    {
        "account_id": "ACCT-0056",
        "account_name": "Brightwell Labs APAC 056",
        "region": "APAC",
        "usage_row_count": 24,
        "compute_hours": 704.83,
        "api_calls": 225914,
    },
    {
        "account_id": "ACCT-0033",
        "account_name": "Northstar Works EMEA 033",
        "region": "EMEA",
        "usage_row_count": 22,
        "compute_hours": 693.86,
        "api_calls": 206021,
    },
    {
        "account_id": "ACCT-0060",
        "account_name": "BluePeak Labs APAC 060",
        "region": "APAC",
        "usage_row_count": 17,
        "compute_hours": 525.48,
        "api_calls": 147626,
    },
    {
        "account_id": "ACCT-0010",
        "account_name": "Harbor Analytics NA 010",
        "region": "NA",
        "usage_row_count": 15,
        "compute_hours": 468.40,
        "api_calls": 136800,
    },
    {
        "account_id": "ACCT-0081",
        "account_name": "Cobalt Systems LATAM 081",
        "region": "LATAM",
        "usage_row_count": 13,
        "compute_hours": 392.09,
        "api_calls": 121073,
    },
]
EXPECTED_REGIONAL_BREAKDOWN = [
    {
        "region": "APAC",
        "account_count": 3,
        "usage_row_count": 53,
        "compute_hours": 1615.09,
        "api_calls": 485685,
    },
    {
        "region": "EMEA",
        "account_count": 2,
        "usage_row_count": 33,
        "compute_hours": 1031.65,
        "api_calls": 320122,
    },
    {
        "region": "LATAM",
        "account_count": 1,
        "usage_row_count": 13,
        "compute_hours": 392.09,
        "api_calls": 121073,
    },
    {
        "region": "NA",
        "account_count": 2,
        "usage_row_count": 24,
        "compute_hours": 741.22,
        "api_calls": 221118,
    },
]

POINTS = [
    ("SP001", 2, "exact approved target usage rows are corrected to LUMAFORMS"),
    ("SP002", 2, "no unrelated database rows or tables are changed"),
    ("SP003", 1, "audit fields are populated for the approved correction"),
    ("SP004", 1, "changed_row_count reports the approved target count"),
    ("SP005", 3, "total_compute_hours_after_fix matches the recomputed metric"),
    ("SP006", 3, "affected_accounts matches qualified corrected commercial accounts"),
    ("SP007", 3, "top_accounts_after_fix and regional_breakdown_after_fix match recomputed metrics"),
]


def db_path():
    env_path = os.environ.get("TASK_SQLITE_DB_PATH")
    if env_path:
        return Path(env_path)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "env" / "generated" / "ops_analytics.sqlite").exists():
            return parent / "env" / "generated" / "ops_analytics.sqlite"
    return here.parents[3] / "env" / "generated" / "ops_analytics.sqlite"


def load_prediction(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def table_names(con):
    return [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]


def table_columns(con, table):
    return [row[1] for row in con.execute(f"PRAGMA table_info({table})")]


def snapshot(con):
    snap = {}
    for table in table_names(con):
        cols = table_columns(con, table)
        order_col = cols[0]
        rows = [dict(zip(cols, row)) for row in con.execute(f"SELECT * FROM {table} ORDER BY {order_col}")]
        snap[table] = {"columns": cols, "rows": rows}
    return snap


def target_ids(con):
    row = con.execute("SELECT target_ids_csv FROM data_quality_cases WHERE case_id = ?", (CASE_ID,)).fetchone()
    if not row:
        return []
    return [part for part in row[0].split(",") if part]


def install_authorizer(con):
    allowed_update_columns = {"product_id", "audit_reason", "audit_updated_at"}
    allowed_actions = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_FUNCTION,
    }
    for name in ("SQLITE_RECURSIVE", "SQLITE_SAVEPOINT"):
        if hasattr(sqlite3, name):
            allowed_actions.add(getattr(sqlite3, name))

    def authorize(action, arg1, arg2, dbname, source):
        if action == sqlite3.SQLITE_UPDATE:
            if arg1 == "usage_daily" and arg2 in allowed_update_columns:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        if action in allowed_actions:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    con.set_authorizer(authorize)


def execute_prediction_sql(database_path, sql):
    if not isinstance(sql, str) or not sql.strip():
        return False, "missing correction_sql"
    with closing(sqlite3.connect(database_path)) as con:
        try:
            install_authorizer(con)
            con.executescript(sql)
            con.commit()
            return True, ""
        except Exception as exc:
            return False, str(exc)


def rows_by_id(snap, table):
    first_col = snap[table]["columns"][0]
    return {row[first_col]: row for row in snap[table]["rows"]}


def target_update_ok(before, after, ids):
    usage_before = rows_by_id(before, "usage_daily")
    usage_after = rows_by_id(after, "usage_daily")
    if set(ids) - set(usage_after):
        return False
    for usage_id in ids:
        if usage_before[usage_id]["product_id"] != SOURCE_PRODUCT:
            return False
        if usage_after[usage_id]["product_id"] != TARGET_PRODUCT:
            return False
    return True


def no_unrelated_changes_ok(before, after, ids):
    allowed_target_changes = {"product_id", "audit_reason", "audit_updated_at"}
    for table in before:
        if table != "usage_daily" and before[table] != after.get(table):
            return False
    if before["usage_daily"]["columns"] != after["usage_daily"]["columns"]:
        return False
    before_usage = rows_by_id(before, "usage_daily")
    after_usage = rows_by_id(after, "usage_daily")
    if set(before_usage) != set(after_usage):
        return False
    id_set = set(ids)
    for usage_id, before_row in before_usage.items():
        after_row = after_usage[usage_id]
        if usage_id not in id_set:
            if before_row != after_row:
                return False
            continue
        for col, before_value in before_row.items():
            if col in allowed_target_changes:
                continue
            if after_row[col] != before_value:
                return False
    return True


def audit_ok(after, ids):
    usage_after = rows_by_id(after, "usage_daily")
    for usage_id in ids:
        row = usage_after.get(usage_id)
        if not row:
            return False
        if row["audit_reason"] != EXPECTED_AUDIT_REASON:
            return False
        if not row["audit_updated_at"]:
            return False
    return True


QUALIFIED_CTE = """
WITH qualified AS (
  SELECT u.*
  FROM usage_daily u
  JOIN accounts a ON a.account_id = u.account_id
  WHERE u.product_id = 'LUMAFORMS'
    AND u.activity_date >= '2026-05-01'
    AND u.activity_date < '2026-06-01'
    AND u.environment = 'production'
    AND u.is_backfill = 0
    AND a.is_internal = 0
    AND a.account_status IN ('active', 'paused')
    AND a.segment = 'commercial'
    AND EXISTS (
      SELECT 1
      FROM subscriptions s
      WHERE s.account_id = u.account_id
        AND s.product_id = u.product_id
        AND s.start_date <= u.activity_date
        AND (s.end_date IS NULL OR s.end_date >= u.activity_date)
        AND s.subscription_status IN ('active', 'paused', 'ended')
    )
    AND NOT (
      u.source_system = 'telemetry_v1'
      AND EXISTS (
        SELECT 1
        FROM usage_daily u2
        WHERE u2.account_id = u.account_id
          AND u2.product_id = u.product_id
          AND u2.activity_date = u.activity_date
          AND u2.environment = 'production'
          AND u2.source_system = 'telemetry_v2'
          AND u2.is_backfill = 0
      )
    )
)
"""


def recompute_metrics(con, ids):
    total = con.execute(QUALIFIED_CTE + "SELECT ROUND(SUM(compute_hours), 2) FROM qualified").fetchone()[0]
    placeholders = ",".join("?" for _ in ids)
    affected = [
        {
            "account_id": row[0],
            "account_name": row[1],
            "region": row[2],
            "corrected_usage_row_count": row[3],
            "added_compute_hours": row[4],
        }
        for row in con.execute(
            QUALIFIED_CTE
            + f"""
SELECT q.account_id, a.account_name, a.region, COUNT(*) AS corrected_usage_row_count,
       ROUND(SUM(q.compute_hours), 2) AS added_compute_hours
FROM qualified q
JOIN accounts a ON a.account_id = q.account_id
WHERE q.usage_id IN ({placeholders})
GROUP BY q.account_id, a.account_name, a.region
ORDER BY q.account_id
""",
            ids,
        )
    ]
    top_accounts = [
        {
            "account_id": row[0],
            "account_name": row[1],
            "region": row[2],
            "usage_row_count": row[3],
            "compute_hours": row[4],
            "api_calls": row[5],
        }
        for row in con.execute(
            QUALIFIED_CTE
            + """
SELECT q.account_id, a.account_name, a.region, COUNT(*) AS usage_row_count,
       ROUND(SUM(q.compute_hours), 2) AS compute_hours, SUM(q.api_calls) AS api_calls
FROM qualified q
JOIN accounts a ON a.account_id = q.account_id
GROUP BY q.account_id, a.account_name, a.region
ORDER BY compute_hours DESC, q.account_id ASC
LIMIT 5
"""
        )
    ]
    regional = [
        {
            "region": row[0],
            "account_count": row[1],
            "usage_row_count": row[2],
            "compute_hours": row[3],
            "api_calls": row[4],
        }
        for row in con.execute(
            QUALIFIED_CTE
            + """
SELECT a.region, COUNT(DISTINCT q.account_id) AS account_count,
       COUNT(*) AS usage_row_count, ROUND(SUM(q.compute_hours), 2) AS compute_hours,
       SUM(q.api_calls) AS api_calls
FROM qualified q
JOIN accounts a ON a.account_id = q.account_id
GROUP BY a.region
ORDER BY a.region ASC
"""
        )
    ]
    return total, affected, top_accounts, regional


def close_number(value, expected, places=2):
    try:
        return abs(round(float(value), places) - round(float(expected), places)) <= 0.5 * (10**-places)
    except Exception:
        return False


def int_eq(actual, expected):
    if isinstance(actual, bool):
        return False
    try:
        return int(actual) == int(expected)
    except (TypeError, ValueError):
        return False


def object_matches(actual, expected, number_fields):
    if not isinstance(actual, dict):
        return False
    for key, expected_value in expected.items():
        if key in number_fields:
            if not close_number(actual.get(key), expected_value):
                return False
        elif isinstance(expected_value, int):
            if not int_eq(actual.get(key), expected_value):
                return False
        else:
            if actual.get(key) != expected_value:
                return False
    return True


def list_matches(actual, expected, number_fields):
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    return all(
        object_matches(actual_obj, expected_obj, number_fields) for actual_obj, expected_obj in zip(actual, expected)
    )


def build_report(results):
    earned_weight = 0
    points = []
    for point_id, weight, goal in POINTS:
        passed = bool(results.get(point_id))
        earned = weight if passed else 0
        earned_weight += earned
        points.append(
            {
                "id": point_id,
                "weight": weight,
                "earned": earned,
                "passed": passed,
                "goal": goal,
            }
        )
    total_weight = sum(weight for _, weight, _ in POINTS)
    return {
        "score": earned_weight / total_weight,
        "earned_weight": earned_weight,
        "total_weight": total_weight,
        "points": points,
    }


def main():
    pred_path = sys.argv[1] if len(sys.argv) > 1 else ""
    pred = load_prediction(pred_path)
    source_db = db_path()
    results = {point_id: False for point_id, _, _ in POINTS}

    if not source_db.exists():
        print(json.dumps(build_report(results), indent=2))
        return

    fd, tmp_path = tempfile.mkstemp(prefix="test_003_eval_", suffix=".sqlite")
    os.close(fd)
    try:
        shutil.copyfile(source_db, tmp_path)
        with closing(sqlite3.connect(tmp_path)) as con:
            before = snapshot(con)
            ids = target_ids(con)

        sql_ok, _ = execute_prediction_sql(tmp_path, pred.get("correction_sql"))

        with closing(sqlite3.connect(tmp_path)) as con:
            after = snapshot(con)

            if sql_ok:
                results["SP001"] = target_update_ok(before, after, ids)
                results["SP002"] = no_unrelated_changes_ok(before, after, ids)
                results["SP003"] = audit_ok(after, ids)

                total, affected, top_accounts, regional = recompute_metrics(con, ids)
                results["SP005"] = close_number(total, EXPECTED_TOTAL_COMPUTE_HOURS) and close_number(
                    pred.get("total_compute_hours_after_fix"), EXPECTED_TOTAL_COMPUTE_HOURS
                )
                results["SP006"] = affected == EXPECTED_AFFECTED_ACCOUNTS and list_matches(
                    pred.get("affected_accounts"),
                    EXPECTED_AFFECTED_ACCOUNTS,
                    {"added_compute_hours"},
                )
                results["SP007"] = (
                    top_accounts == EXPECTED_TOP_ACCOUNTS
                    and regional == EXPECTED_REGIONAL_BREAKDOWN
                    and list_matches(
                        pred.get("top_accounts_after_fix"),
                        EXPECTED_TOP_ACCOUNTS,
                        {"compute_hours"},
                    )
                    and list_matches(
                        pred.get("regional_breakdown_after_fix"),
                        EXPECTED_REGIONAL_BREAKDOWN,
                        {"compute_hours"},
                    )
                )

        results["SP004"] = pred.get("changed_row_count") == EXPECTED_CHANGED_ROW_COUNT
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    print(json.dumps(build_report(results), indent=2))


if __name__ == "__main__":
    main()
