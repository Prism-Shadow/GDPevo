#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from pathlib import Path


TOTAL_WEIGHT = 16
SEVERITIES = ("P1", "P2", "P3", "P4")


def db_path() -> Path:
    env_path = os.environ.get("TASK_SQLITE_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[3] / "env" / "generated" / "ops_analytics.sqlite"


def read_prediction(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def int_or_none(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def round2_or_none(value):
    if isinstance(value, bool):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def severity_counts(value):
    if not isinstance(value, dict):
        return None
    out = {}
    for sev in SEVERITIES:
        parsed = int_or_none(value.get(sev))
        if parsed is None:
            return None
        out[sev] = parsed
    return out


def account_usage_map(items):
    if not isinstance(items, list):
        return None
    out = {}
    for item in items:
        if not isinstance(item, dict):
            return None
        account_id = item.get("account_id")
        if not isinstance(account_id, str):
            return None
        api_calls = int_or_none(item.get("api_calls"))
        compute_hours = round2_or_none(item.get("compute_hours"))
        if api_calls is None or compute_hours is None:
            return None
        out[account_id] = {"api_calls": api_calls, "compute_hours": compute_hours}
    return out


def followup_map(items):
    if not isinstance(items, list):
        return None
    out = {}
    for item in items:
        if not isinstance(item, dict):
            return None
        account_id = item.get("account_id")
        if not isinstance(account_id, str):
            return None
        ticket_count = int_or_none(item.get("ticket_count"))
        sev = severity_counts(item.get("severity_counts"))
        if ticket_count is None or sev is None:
            return None
        out[account_id] = {"ticket_count": ticket_count, "severity_counts": sev}
    return out


def expected(conn: sqlite3.Connection):
    conn.row_factory = sqlite3.Row
    incident = dict(conn.execute(
        "SELECT incident_id, product_id, started_at, resolved_at, severity, impacted_region "
        "FROM incidents WHERE incident_id = ?",
        ("INC-2026-005",),
    ).fetchone())

    usage_sql = """
    WITH inc AS (
      SELECT * FROM incidents WHERE incident_id = 'INC-2026-005'
    ), candidate_usage AS (
      SELECT u.*
      FROM usage_daily u
      JOIN inc ON inc.product_id = u.product_id
      JOIN accounts a ON a.account_id = u.account_id
      WHERE u.activity_date BETWEEN date(inc.started_at) AND date(inc.resolved_at)
        AND (inc.impacted_region = 'GLOBAL' OR a.region = inc.impacted_region)
    ), eligible_usage AS (
      SELECT cu.*
      FROM candidate_usage cu
      JOIN accounts a ON a.account_id = cu.account_id
      WHERE a.is_internal = 0
        AND a.account_status = 'active'
        AND cu.environment = 'production'
        AND cu.is_backfill = 0
        AND EXISTS (
          SELECT 1
          FROM subscriptions s
          WHERE s.account_id = cu.account_id
            AND s.product_id = cu.product_id
            AND s.subscription_status = 'active'
            AND s.start_date <= cu.activity_date
            AND (s.end_date IS NULL OR s.end_date >= cu.activity_date)
        )
    ), qualified_usage AS (
      SELECT eu.*
      FROM eligible_usage eu
      WHERE eu.source_system <> 'telemetry_v1'
         OR NOT EXISTS (
          SELECT 1
          FROM eligible_usage newer
          WHERE newer.account_id = eu.account_id
            AND newer.product_id = eu.product_id
            AND newer.activity_date = eu.activity_date
            AND newer.source_system = 'telemetry_v2'
        )
    )
    SELECT q.account_id, a.account_name, SUM(q.api_calls) AS api_calls,
           ROUND(SUM(q.compute_hours), 2) AS compute_hours
    FROM qualified_usage q
    JOIN accounts a ON a.account_id = q.account_id
    GROUP BY q.account_id, a.account_name
    ORDER BY api_calls DESC, q.account_id
    """
    impacted_accounts = [dict(row) for row in conn.execute(usage_sql)]
    total_api_calls = sum(row["api_calls"] for row in impacted_accounts)
    highest_usage_account = impacted_accounts[0] if impacted_accounts else None

    followup_sql = """
    WITH inc AS (
      SELECT * FROM incidents WHERE incident_id = 'INC-2026-005'
    ), followup_tickets AS (
      SELECT t.*
      FROM tickets t
      JOIN inc ON inc.product_id = t.product_id
      JOIN accounts a ON a.account_id = t.account_id
      WHERE t.created_at > inc.resolved_at
        AND t.created_at <= datetime(inc.resolved_at, '+7 days')
        AND (inc.impacted_region = 'GLOBAL' OR a.region = inc.impacted_region)
        AND a.is_internal = 0
        AND a.account_status = 'active'
        AND t.status <> 'canceled'
        AND t.is_duplicate = 0
        AND t.customer_impact = 1
        AND t.category IN ('bug', 'outage', 'performance', 'data_loss')
        AND (t.linked_incident_id IS NULL OR t.linked_incident_id = inc.incident_id)
    )
    SELECT ft.account_id, a.account_name, COUNT(*) AS ticket_count,
           SUM(CASE WHEN ft.severity = 'P1' THEN 1 ELSE 0 END) AS P1,
           SUM(CASE WHEN ft.severity = 'P2' THEN 1 ELSE 0 END) AS P2,
           SUM(CASE WHEN ft.severity = 'P3' THEN 1 ELSE 0 END) AS P3,
           SUM(CASE WHEN ft.severity = 'P4' THEN 1 ELSE 0 END) AS P4
    FROM followup_tickets ft
    JOIN accounts a ON a.account_id = ft.account_id
    GROUP BY ft.account_id, a.account_name
    ORDER BY ft.account_id
    """
    followup_accounts = []
    for row in conn.execute(followup_sql):
        item = dict(row)
        followup_accounts.append({
            "account_id": item["account_id"],
            "account_name": item["account_name"],
            "ticket_count": item["ticket_count"],
            "severity_counts": {sev: item[sev] for sev in SEVERITIES},
        })

    severity_mix = {sev: 0 for sev in SEVERITIES}
    for account in followup_accounts:
        for sev in SEVERITIES:
            severity_mix[sev] += account["severity_counts"][sev]

    exclusion_sql = """
    WITH inc AS (
      SELECT * FROM incidents WHERE incident_id = 'INC-2026-005'
    ), candidate_usage AS (
      SELECT u.*
      FROM usage_daily u
      JOIN inc ON inc.product_id = u.product_id
      JOIN accounts a ON a.account_id = u.account_id
      WHERE u.activity_date BETWEEN date(inc.started_at) AND date(inc.resolved_at)
        AND (inc.impacted_region = 'GLOBAL' OR a.region = inc.impacted_region)
    ), eligible_usage AS (
      SELECT cu.*
      FROM candidate_usage cu
      JOIN accounts a ON a.account_id = cu.account_id
      WHERE a.is_internal = 0
        AND a.account_status = 'active'
        AND cu.environment = 'production'
        AND cu.is_backfill = 0
        AND EXISTS (
          SELECT 1 FROM subscriptions s
          WHERE s.account_id = cu.account_id
            AND s.product_id = cu.product_id
            AND s.subscription_status = 'active'
            AND s.start_date <= cu.activity_date
            AND (s.end_date IS NULL OR s.end_date >= cu.activity_date)
        )
    )
    SELECT
      (SELECT COUNT(*) FROM candidate_usage) AS usage_candidate_rows,
      (SELECT COUNT(*) FROM candidate_usage WHERE environment <> 'production') AS usage_non_production_rows_excluded,
      (SELECT COUNT(*) FROM candidate_usage WHERE is_backfill = 1) AS usage_backfill_rows_excluded,
      (SELECT COUNT(*) FROM candidate_usage cu JOIN accounts a ON a.account_id = cu.account_id
       WHERE a.is_internal = 1 OR a.account_status <> 'active') AS usage_internal_or_inactive_account_rows_excluded,
      (SELECT COUNT(*) FROM candidate_usage cu
       WHERE NOT EXISTS (
         SELECT 1 FROM subscriptions s
         WHERE s.account_id = cu.account_id
           AND s.product_id = cu.product_id
           AND s.subscription_status = 'active'
           AND s.start_date <= cu.activity_date
           AND (s.end_date IS NULL OR s.end_date >= cu.activity_date)
       )) AS usage_without_active_subscription_rows_excluded,
      (SELECT COUNT(*) FROM eligible_usage eu
       WHERE eu.source_system = 'telemetry_v1'
         AND EXISTS (
           SELECT 1 FROM eligible_usage newer
           WHERE newer.account_id = eu.account_id
             AND newer.product_id = eu.product_id
             AND newer.activity_date = eu.activity_date
             AND newer.source_system = 'telemetry_v2'
         )) AS usage_telemetry_v1_overlap_rows_excluded,
      (SELECT COUNT(*)
       FROM tickets t JOIN inc ON inc.product_id = t.product_id JOIN accounts a ON a.account_id = t.account_id
       WHERE t.created_at > inc.resolved_at
         AND t.created_at <= datetime(inc.resolved_at, '+7 days')
         AND (inc.impacted_region = 'GLOBAL' OR a.region = inc.impacted_region)) AS ticket_candidates_in_followup_window,
      (SELECT COUNT(*)
       FROM tickets t JOIN inc ON inc.product_id = t.product_id JOIN accounts a ON a.account_id = t.account_id
       WHERE t.created_at > inc.resolved_at
         AND t.created_at <= datetime(inc.resolved_at, '+7 days')
         AND (inc.impacted_region = 'GLOBAL' OR a.region = inc.impacted_region)
         AND (t.status = 'canceled' OR t.is_duplicate = 1)) AS ticket_canceled_or_duplicate_excluded,
      (SELECT COUNT(*)
       FROM tickets t JOIN inc ON inc.product_id = t.product_id JOIN accounts a ON a.account_id = t.account_id
       WHERE t.created_at > inc.resolved_at
         AND t.created_at <= datetime(inc.resolved_at, '+7 days')
         AND (inc.impacted_region = 'GLOBAL' OR a.region = inc.impacted_region)
         AND (t.customer_impact = 0
              OR t.category NOT IN ('bug', 'outage', 'performance', 'data_loss')
              OR a.is_internal = 1
              OR a.account_status <> 'active')) AS ticket_non_customer_impact_excluded
    """
    excluded_counts = dict(conn.execute(exclusion_sql).fetchone())

    return {
        "incident": incident,
        "followup_end": conn.execute(
            "SELECT datetime(resolved_at, '+7 days') FROM incidents WHERE incident_id = 'INC-2026-005'"
        ).fetchone()[0],
        "impacted_accounts": impacted_accounts,
        "impacted_account_count": len(impacted_accounts),
        "total_api_calls": total_api_calls,
        "highest_usage_account": highest_usage_account,
        "followup_accounts": followup_accounts,
        "severity_mix": severity_mix,
        "excluded_counts": excluded_counts,
    }


def point(point_id, weight, passed, goal):
    earned = weight if passed else 0
    return {"id": point_id, "weight": weight, "earned": earned, "passed": bool(passed), "goal": goal}


def evaluate(pred, exp):
    points = []
    incident_window = pred.get("incident_window") if isinstance(pred, dict) else None
    followup_window = pred.get("followup_ticket_window") if isinstance(pred, dict) else None
    incident_ok = (
        pred.get("incident_id") == exp["incident"]["incident_id"]
        and pred.get("product_id") == exp["incident"]["product_id"]
        and isinstance(incident_window, dict)
        and incident_window.get("started_at") == exp["incident"]["started_at"]
        and incident_window.get("resolved_at") == exp["incident"]["resolved_at"]
        and incident_window.get("impacted_region") == exp["incident"]["impacted_region"]
        and incident_window.get("incident_severity") == exp["incident"]["severity"]
        and isinstance(followup_window, dict)
        and followup_window.get("start_exclusive") == exp["incident"]["resolved_at"]
        and followup_window.get("end_inclusive") == exp["followup_end"]
    )
    points.append(point("SP001", 2, incident_ok, "Use the database incident window, impacted region, severity, and seven-day follow-up window."))

    predicted_accounts = account_usage_map(pred.get("impacted_accounts"))
    expected_accounts = {
        row["account_id"]: {"api_calls": row["api_calls"], "compute_hours": round(row["compute_hours"], 2)}
        for row in exp["impacted_accounts"]
    }
    account_set_ok = (
        predicted_accounts == expected_accounts
        and int_or_none(pred.get("impacted_account_count")) == exp["impacted_account_count"]
    )
    points.append(point("SP002", 3, account_set_ok, "Identify the exact impacted account set and per-account usage."))

    total_ok = int_or_none(pred.get("total_api_calls")) == exp["total_api_calls"]
    points.append(point("SP003", 2, total_ok, "Report exact total qualified API calls during the incident window."))

    predicted_highest = pred.get("highest_usage_account")
    highest = exp["highest_usage_account"] or {}
    highest_ok = (
        isinstance(predicted_highest, dict)
        and predicted_highest.get("account_id") == highest.get("account_id")
        and int_or_none(predicted_highest.get("api_calls")) == highest.get("api_calls")
        and round2_or_none(predicted_highest.get("compute_hours")) == round(highest.get("compute_hours", 0), 2)
    )
    points.append(point("SP004", 2, highest_ok, "Return the highest-usage account by API calls with deterministic tie handling."))

    predicted_followup = followup_map(pred.get("accounts_with_followup_tickets"))
    expected_followup = {
        row["account_id"]: {
            "ticket_count": row["ticket_count"],
            "severity_counts": row["severity_counts"],
        }
        for row in exp["followup_accounts"]
    }
    points.append(point("SP005", 2, predicted_followup == expected_followup, "Identify accounts with qualifying follow-up tickets and their counts."))

    points.append(point("SP006", 1, severity_counts(pred.get("severity_mix")) == exp["severity_mix"], "Report the qualifying follow-up ticket severity mix."))

    predicted_exclusions = pred.get("excluded_counts")
    exclusions_ok = False
    if isinstance(predicted_exclusions, dict):
        exclusions_ok = all(
            int_or_none(predicted_exclusions.get(k)) == v
            for k, v in exp["excluded_counts"].items()
        )
    points.append(point("SP007", 2, exclusions_ok, "Report the expected usage and ticket exclusion diagnostics."))

    schema_ok = all(key in pred for key in (
        "incident_id",
        "product_id",
        "incident_window",
        "followup_ticket_window",
        "impacted_account_count",
        "total_api_calls",
        "impacted_accounts",
        "accounts_with_followup_tickets",
        "highest_usage_account",
        "severity_mix",
        "excluded_counts",
    ))
    points.append(point("SP008", 2, schema_ok, "Use the required JSON response structure."))

    earned = sum(p["earned"] for p in points)
    return {
        "score": earned / TOTAL_WEIGHT,
        "earned_weight": earned,
        "total_weight": TOTAL_WEIGHT,
        "points": points,
    }


def zero_report(message):
    return {
        "score": 0.0,
        "earned_weight": 0,
        "total_weight": TOTAL_WEIGHT,
        "points": [
            {"id": "ERR", "weight": TOTAL_WEIGHT, "earned": 0, "passed": False, "goal": message}
        ],
    }


def main():
    if len(sys.argv) != 2:
        print(json.dumps(zero_report("Provide a prediction JSON path as the only argument.")))
        return
    try:
        pred = read_prediction(sys.argv[1])
    except Exception as exc:
        print(json.dumps(zero_report(f"Prediction JSON could not be read: {exc}")))
        return
    if not isinstance(pred, dict):
        print(json.dumps(zero_report("Prediction JSON must be an object.")))
        return

    path = db_path()
    try:
        conn = sqlite3.connect(path)
        exp = expected(conn)
    except Exception as exc:
        print(json.dumps(zero_report(f"Could not compute expected answer from SQLite: {exc}")))
        return

    print(json.dumps(evaluate(pred, exp), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
