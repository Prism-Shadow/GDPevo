#!/usr/bin/env python3
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path


TARGET_IDS = {
    "TKT-DQ-MAY-D-001",
    "TKT-DQ-MAY-D-002",
}
MASTER_ID = "TKT-DQ-MASTER-05-D"
CASE_ID = "DQ-TKT-2026-05-D"
AUDIT_REASON = "approved correction DQ-TKT-2026-05-D"
AUDIT_UPDATED_AT = "2026-05-29 12:05:00"
PRODUCT_ID = "LUMAFORMS"
PERIOD_START = "2026-05-01 00:00:00"
PERIOD_END = "2026-06-01 00:00:00"
SEVERITIES = ["P1", "P2", "P3", "P4"]
SEVERITY_RANK = {sev: idx for idx, sev in enumerate(SEVERITIES)}


def task_group_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "env" / "generated" / "ops_analytics.sqlite").exists():
            return parent
    return here.parents[3]


def db_path() -> Path:
    env_path = os.environ.get("TASK_SQLITE_DB_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
    return task_group_root() / "env" / "generated" / "ops_analytics.sqlite"


def load_prediction(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def connect(path: Path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def ticket_snapshot(con):
    rows = con.execute("SELECT * FROM tickets ORDER BY ticket_id").fetchall()
    return {row["ticket_id"]: dict(row) for row in rows}


def table_names(con):
    rows = con.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row["name"] for row in rows]


def non_ticket_snapshot(con):
    snapshot = {}
    for table in table_names(con):
        if table == "tickets":
            continue
        columns = [row["name"] for row in con.execute(f'PRAGMA table_info("{table}")').fetchall()]
        order_by = ", ".join(f'"{col}"' for col in columns)
        rows = con.execute(f'SELECT * FROM "{table}" ORDER BY {order_by}').fetchall()
        snapshot[table] = [dict(row) for row in rows]
    return snapshot


def ticket_change_columns(before_row, after_row):
    return {key for key in before_row.keys() if before_row.get(key) != after_row.get(key)}


def execute_prediction_sql(source: Path, correction_sql: str):
    tmpdir = tempfile.TemporaryDirectory()
    tmp_path = Path(tmpdir.name) / "candidate.sqlite"
    shutil.copy2(source, tmp_path)
    con = connect(tmp_path)
    before = ticket_snapshot(con)
    before_other = non_ticket_snapshot(con)
    error = None
    try:
        con.executescript(correction_sql)
        con.commit()
    except Exception as exc:
        con.rollback()
        error = str(exc)
    after = ticket_snapshot(con)
    after_other = non_ticket_snapshot(con)
    return tmpdir, con, before, after, before_other, after_other, error


def qualified_where_clause():
    return """
    FROM tickets t
    JOIN accounts a ON a.account_id = t.account_id
    WHERE t.product_id = 'LUMAFORMS'
      AND t.created_at >= ?
      AND t.created_at < ?
      AND t.status <> 'canceled'
      AND a.is_internal = 0
      AND a.account_status <> 'test'
      AND t.customer_impact = 1
      AND t.category IN ('bug', 'outage', 'performance', 'data_loss')
      AND t.is_duplicate = 0
      AND t.duplicate_of IS NULL
    """


def compute_metrics(con):
    base = qualified_where_clause()
    count = con.execute("SELECT COUNT(*) AS n " + base, (PERIOD_START, PERIOD_END)).fetchone()["n"]

    backlog_rows = con.execute(
        """
        SELECT t.severity, COUNT(*) AS n
        """
        + base
        + """
          AND (t.closed_at IS NULL OR t.closed_at >= ?)
        GROUP BY t.severity
        """,
        (PERIOD_START, PERIOD_END, PERIOD_END),
    ).fetchall()
    backlog = dict.fromkeys(SEVERITIES, 0)
    for row in backlog_rows:
        backlog[row["severity"]] = row["n"]

    breach_row = con.execute(
        """
        SELECT
          COUNT(*) AS n,
          SUM(CASE
                WHEN COALESCE(t.closed_at, ?) > t.sla_due_at THEN 1
                ELSE 0
              END) AS breached
        """
        + base,
        (PERIOD_END, PERIOD_START, PERIOD_END),
    ).fetchone()
    breached = breach_row["breached"] or 0
    breach_rate = round(breached / breach_row["n"], 4) if breach_row["n"] else 0.0

    account_rows = con.execute(
        """
        SELECT
          t.account_id,
          a.account_name,
          COUNT(*) AS backlog_ticket_count,
          MIN(CASE t.severity
                WHEN 'P1' THEN 1
                WHEN 'P2' THEN 2
                WHEN 'P3' THEN 3
                WHEN 'P4' THEN 4
              END) AS severity_rank,
          SUM(CASE
                WHEN COALESCE(t.closed_at, ?) > t.sla_due_at THEN 1
                ELSE 0
              END) AS breached_backlog_ticket_count
        """
        + base
        + """
          AND (t.closed_at IS NULL OR t.closed_at >= ?)
        GROUP BY t.account_id, a.account_name
        """,
        (PERIOD_END, PERIOD_START, PERIOD_END, PERIOD_END),
    ).fetchall()
    accounts = []
    for row in account_rows:
        severity = SEVERITIES[row["severity_rank"] - 1]
        accounts.append(
            {
                "account_id": row["account_id"],
                "account_name": row["account_name"],
                "backlog_ticket_count": row["backlog_ticket_count"],
                "highest_severity": severity,
                "breached_backlog_ticket_count": row["breached_backlog_ticket_count"] or 0,
            }
        )
    accounts.sort(
        key=lambda item: (
            -item["backlog_ticket_count"],
            SEVERITY_RANK[item["highest_severity"]],
            item["account_id"],
        )
    )

    return {
        "qualified_ticket_count_after_fix": count,
        "backlog_by_severity": backlog,
        "sla_breach_rate_after_fix": breach_rate,
        "accounts_to_notify": accounts,
    }


def normalize_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def normalize_rate(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value), 4)


def compare_backlog(pred, expected):
    if not isinstance(pred, dict):
        return False
    normalized = {}
    for sev in SEVERITIES:
        value = pred.get(sev)
        if normalize_int(value) is None:
            return False
        normalized[sev] = value
    return normalized == expected


def compare_accounts(pred, expected):
    if not isinstance(pred, list):
        return False
    return pred == expected


def make_point(point_id, weight, passed, goal, detail=None):
    point = {
        "id": point_id,
        "weight": weight,
        "earned": weight if passed else 0,
        "passed": bool(passed),
        "goal": goal,
    }
    if detail:
        point["detail"] = detail
    return point


def main():
    total_weight = 18
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": total_weight,
                    "points": [],
                    "error": "usage: eval.sh <prediction.json>",
                }
            )
        )
        return 1

    try:
        pred = load_prediction(sys.argv[1])
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": total_weight,
                    "points": [],
                    "error": f"could not read prediction JSON: {exc}",
                }
            )
        )
        return 0

    correction_sql = pred.get("correction_sql")
    if not isinstance(correction_sql, str):
        correction_sql = ""

    source_db = db_path()
    tmpdir = None
    try:
        tmpdir, con, before, after, before_other, after_other, sql_error = execute_prediction_sql(
            source_db, correction_sql
        )

        target_exact = True
        audit_ok = True
        for ticket_id in TARGET_IDS:
            before_row = before.get(ticket_id)
            after_row = after.get(ticket_id)
            if before_row is None or after_row is None:
                target_exact = False
                audit_ok = False
                continue
            changed_cols = ticket_change_columns(before_row, after_row)
            target_exact = target_exact and changed_cols == {
                "is_duplicate",
                "duplicate_of",
                "audit_reason",
                "audit_updated_at",
            }
            target_exact = target_exact and before_row["product_id"] == PRODUCT_ID
            target_exact = target_exact and after_row["is_duplicate"] == 1
            target_exact = target_exact and after_row["duplicate_of"] == MASTER_ID
            audit_ok = audit_ok and after_row["audit_reason"] == AUDIT_REASON
            audit_ok = audit_ok and after_row["audit_updated_at"] == AUDIT_UPDATED_AT

        unrelated_ok = True
        changed_ticket_ids = set()
        for ticket_id, before_row in before.items():
            after_row = after.get(ticket_id)
            if after_row is None:
                unrelated_ok = False
                changed_ticket_ids.add(ticket_id)
                continue
            if before_row != after_row:
                changed_ticket_ids.add(ticket_id)
                if ticket_id not in TARGET_IDS:
                    unrelated_ok = False
        for ticket_id in after.keys() - before.keys():
            unrelated_ok = False
            changed_ticket_ids.add(ticket_id)
        if before_other != after_other:
            unrelated_ok = False

        actual_changed_count = len(changed_ticket_ids)
        metrics = compute_metrics(con)

        points = [
            make_point(
                "SP001",
                3,
                sql_error is None and target_exact,
                "correction_sql marks exactly the approved May duplicate tickets against the master ticket",
                sql_error,
            ),
            make_point(
                "SP002",
                3,
                sql_error is None and unrelated_ok,
                "correction_sql does not change unrelated ticket rows or non-ticket tables",
            ),
            make_point(
                "SP003",
                2,
                sql_error is None and audit_ok,
                "correction_sql writes the required audit_reason and audit_updated_at values",
            ),
            make_point(
                "SP004",
                1,
                normalize_int(pred.get("changed_ticket_count")) == 2 and actual_changed_count == 2,
                "changed_ticket_count is 2",
            ),
            make_point(
                "SP005",
                2,
                normalize_int(pred.get("qualified_ticket_count_after_fix"))
                == metrics["qualified_ticket_count_after_fix"],
                "qualified_ticket_count_after_fix matches the recomputed corrected database",
            ),
            make_point(
                "SP006",
                2,
                compare_backlog(pred.get("backlog_by_severity"), metrics["backlog_by_severity"]),
                "backlog_by_severity matches the recomputed corrected database",
            ),
            make_point(
                "SP007",
                3,
                normalize_rate(pred.get("sla_breach_rate_after_fix")) == metrics["sla_breach_rate_after_fix"],
                "sla_breach_rate_after_fix matches the recomputed corrected database",
            ),
            make_point(
                "SP008",
                2,
                compare_accounts(pred.get("accounts_to_notify"), metrics["accounts_to_notify"]),
                "accounts_to_notify matches the recomputed corrected database in the required order",
            ),
        ]

        earned = sum(point["earned"] for point in points)
        total = sum(point["weight"] for point in points)
        print(
            json.dumps(
                {
                    "score": round(earned / total, 6) if total else 0.0,
                    "earned_weight": earned,
                    "total_weight": total,
                    "points": points,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": total_weight,
                    "points": [],
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    finally:
        if tmpdir is not None:
            tmpdir.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
