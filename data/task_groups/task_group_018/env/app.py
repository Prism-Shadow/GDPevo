import json
import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request
from judge_api import create_judge_blueprint


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TASK_ENV_DB", BASE_DIR / "generated" / "court_ops.db"))

TABLE_FILTERS = {
    "jurisdictions": {"jurisdiction_code", "state", "county"},
    "cases": {"case_number", "jurisdiction_code", "defendant", "status", "case_type"},
    "charges": {"case_number", "offense_code", "statute", "disposition", "severity"},
    "docket_entries": {"case_number", "entry_type", "source"},
    "citations": {"citation_number", "jurisdiction_code", "violation_code", "status", "plea"},
    "fee_schedules": {"jurisdiction_code", "fee_type", "violation_code", "statute"},
    "payment_policies": {"jurisdiction_code", "policy_name"},
    "form_catalog": {"form_id", "jurisdiction_code"},
    "financial_petitions": {"petition_id", "case_number", "jurisdiction_code", "default_status"},
}

ENDPOINT_TABLES = {
    "/api/jurisdictions": "jurisdictions",
    "/api/cases": "cases",
    "/api/charges": "charges",
    "/api/docket-entries": "docket_entries",
    "/api/citations": "citations",
    "/api/fee-schedules": "fee_schedules",
    "/api/payment-policies": "payment_policies",
    "/api/forms": "form_catalog",
    "/api/financial-petitions": "financial_petitions",
}

REDACTED_RESPONSE_FIELDS = {
    "cases": {
        "notes",
    },
    "citations": {
        "standard_fine",
        "county_surcharge",
        "amount_due",
        "final_payment_amount",
        "plan_notes",
    },
    "financial_petitions": {
        "approved_monthly",
        "first_due_date",
        "final_due_date",
        "return_to_court_date",
        "account_fee_applicable",
        "notes",
    },
}


def create_app():
    app = Flask(__name__)

    @app.get("/health")
    def health():
        ok = DB_PATH.exists()
        table_counts = {}
        if ok:
            try:
                with connect() as conn:
                    for table in ENDPOINT_TABLES.values():
                        table_counts[table] = conn.execute(f"select count(*) from {table}").fetchone()[0]
            except sqlite3.Error:
                ok = False
                table_counts = {}
        return jsonify(
            {
                "status": "ok" if ok else "degraded",
                "service": "court-operations-portal",
                "database_available": ok,
                "state_mode": "read_only",
                "judge_enabled": os.environ.get("TASK_ENV_ENABLE_JUDGE") == "1",
                "table_counts": table_counts,
            }
        ), 200 if ok else 503

    for route, table in ENDPOINT_TABLES.items():
        app.add_url_rule(route, endpoint=f"{table}_api", view_func=_make_table_view(table), methods=["GET"])

    @app.get("/api/search")
    def search():
        q = request.args.get("q", "").strip()
        if len(q) < 2:
            return jsonify({"query": q, "count": 0, "results": []})
        like = f"%{q.lower()}%"
        results = []
        specs = [
            ("cases", "case_number", "defendant_first || ' ' || defendant_last || ' ' || case_number"),
            ("charges", "case_number", "offense_code || ' ' || statute || ' ' || description"),
            ("docket_entries", "case_number", "entry_type || ' ' || case_number || ' ' || source"),
            ("citations", "citation_number", "defendant_name || ' ' || violation_code || ' ' || violation_desc"),
            ("financial_petitions", "petition_id", "case_number || ' ' || petitioner_name || ' ' || petition_id"),
            (
                "fee_schedules",
                "fee_id",
                "jurisdiction_code || ' ' || fee_type || ' ' || coalesce(violation_code, '') || ' ' || label",
            ),
            ("form_catalog", "form_id", "form_name || ' ' || placeholder_instruction"),
        ]
        with connect() as conn:
            for table, identifier_col, haystack in specs:
                rows = conn.execute(
                    f"""
                    select *, '{table}' as result_type, {identifier_col} as result_id
                    from {table}
                    where lower({haystack}) like ?
                    order by result_id
                    limit 25
                    """,
                    (like,),
                ).fetchall()
                results.extend([row_to_dict(row, table) for row in rows])
        results.sort(key=lambda item: (item["result_type"], str(item["result_id"])))
        return jsonify({"query": q, "count": len(results), "results": results[:100]})

    if os.environ.get("TASK_ENV_ENABLE_JUDGE") == "1":
        app.register_blueprint(create_judge_blueprint())

    return app


def _make_table_view(table):
    def view():
        where, params = _build_filters(table, request.args)
        order_by = _default_order(table)
        sql = f"select * from {table}"
        if where:
            sql += " where " + " and ".join(where)
        sql += f" order by {order_by} limit ?"
        limit = _limit_arg()
        with connect() as conn:
            rows = conn.execute(sql, (*params, limit)).fetchall()
        return jsonify({"count": len(rows), "results": [row_to_dict(row, table) for row in rows]})

    return view


def _build_filters(table, args):
    where = []
    params = []
    allowed = TABLE_FILTERS[table]
    for key in allowed:
        value = args.get(key)
        if value is None or value == "":
            continue
        if table == "cases" and key == "defendant":
            where.append("lower(defendant_first || ' ' || defendant_last) like ?")
            params.append(f"%{value.lower()}%")
        else:
            where.append(f"{key} = ?")
            params.append(value)

    if table == "fee_schedules":
        effective_on = args.get("effective_on")
        if effective_on:
            where.append("effective_date <= ?")
            params.append(effective_on)
            where.append("(end_date is null or end_date >= ?)")
            params.append(effective_on)

    return where, params


def _limit_arg():
    try:
        return min(500, max(1, int(request.args.get("limit", "100"))))
    except ValueError:
        return 100


def _default_order(table):
    return {
        "jurisdictions": "jurisdiction_code",
        "cases": "case_number",
        "charges": "case_number, count_no",
        "docket_entries": "case_number, entry_date, entry_id",
        "citations": "citation_number",
        "fee_schedules": "jurisdiction_code, fee_type, effective_date desc, fee_id",
        "payment_policies": "jurisdiction_code, policy_name",
        "form_catalog": "jurisdiction_code, form_id",
        "financial_petitions": "petition_id",
    }[table]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row, table=None):
    out = {}
    redacted = REDACTED_RESPONSE_FIELDS.get(table or "", set())
    for key in row.keys():
        if key in redacted:
            continue
        value = row[key]
        if key in {"required_fields"} and isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        if key in {"public_assistance", "mandatory", "plan_approved", "account_fee_applicable", "active"}:
            if value is not None:
                value = bool(value)
        if table == "docket_entries" and key == "text" and row["entry_type"] == "clerk_note":
            value = "Clerk note text redacted from public portal response."
        out[key] = value
    return out


if __name__ == "__main__":
    bind = os.environ.get("TASK_ENV_BIND", "0.0.0.0")
    port = int(os.environ.get("TASK_ENV_PORT", "9018"))
    create_app().run(host=bind, port=port)
